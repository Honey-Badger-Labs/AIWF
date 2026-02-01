terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "compute" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

# VPC Network
resource "google_compute_network" "aiwf_network" {
  name                    = "aiwf-network"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.compute]
}

# Subnet
resource "google_compute_subnetwork" "aiwf_subnet" {
  name          = "aiwf-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.region
  network       = google_compute_network.aiwf_network.id
}

# Firewall - Allow SSH
resource "google_compute_firewall" "aiwf_allow_ssh" {
  name    = "aiwf-allow-ssh"
  network = google_compute_network.aiwf_network.id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["aiwf-vm"]
}

# Firewall - Allow OpenClaw (8080)
resource "google_compute_firewall" "aiwf_allow_openclaw" {
  name    = "aiwf-allow-openclaw"
  network = google_compute_network.aiwf_network.id

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["aiwf-vm"]
}

# Firewall - Allow SustainBot (5000)
resource "google_compute_firewall" "aiwf_allow_sustainbot" {
  name    = "aiwf-allow-sustainbot"
  network = google_compute_network.aiwf_network.id

  allow {
    protocol = "tcp"
    ports    = ["5000"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["aiwf-vm"]
}

# Service Account
resource "google_service_account" "aiwf_sa" {
  account_id   = "aiwf-service-account"
  display_name = "AIWF Service Account"
}

# Grant compute permissions
resource "google_project_iam_member" "aiwf_sa_compute_admin" {
  project = var.project_id
  role    = "roles/compute.admin"
  member  = "serviceAccount:${google_service_account.aiwf_sa.email}"
}

# Linux VM Instance
resource "google_compute_instance" "aiwf_compute" {
  name         = "aiwf-compute-1"
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["aiwf-vm", "http-server", "https-server"]

  depends_on = [google_project_service.compute]

  boot_disk {
    initialize_params {
      image = "projects/debian-cloud/global/images/debian-12-bookworm-v20240110"
      size  = 20
      type  = "pd-standard"
    }
  }

  network_interface {
    network    = google_compute_network.aiwf_network.id
    subnetwork = google_compute_subnetwork.aiwf_subnet.id

    access_config {
      # Ephemeral public IP
    }
  }

  metadata = {
    enable-oslogin = true
  }

  metadata_startup_script = base64encode(file("${path.module}/startup-script.sh"))

  service_account {
    email  = google_service_account.aiwf_sa.email
    scopes = ["cloud-platform"]
  }

  labels = {
    environment = var.environment
    project     = "aiwf"
    managed_by  = "terraform"
  }
}

output "instance_name" {
  value = google_compute_instance.aiwf_compute.name
}

output "instance_public_ip" {
  value = google_compute_instance.aiwf_compute.network_interface[0].access_config[0].nat_ip
}

output "instance_private_ip" {
  value = google_compute_instance.aiwf_compute.network_interface[0].network_interface_ip
}

output "openclaw_url" {
  value = "http://${google_compute_instance.aiwf_compute.network_interface[0].access_config[0].nat_ip}:8080"
}

output "sustainbot_url" {
  value = "http://${google_compute_instance.aiwf_compute.network_interface[0].access_config[0].nat_ip}:5000"
}

output "ssh_command" {
  value = "gcloud compute ssh ${google_compute_instance.aiwf_compute.name} --zone=${google_compute_instance.aiwf_compute.zone}"
}
