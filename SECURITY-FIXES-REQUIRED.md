# AIWF - Critical Security Fixes (Before Deployment)

**Status:** 🚨 REQUIRED BEFORE STAGING DEPLOYMENT  
**Effort:** ~6 hours  
**Blockers:** 5 critical issues

---

## Issue #1: SSH Open to Internet

### 🚨 Current State (INSECURE)
```hcl
# terraform/main.tf:42-49
resource "google_compute_firewall" "allow_ssh" {
  name    = "aiwf-allow-ssh"
  network = google_compute_network.aiwf_network.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]  # ❌ ANYONE CAN SSH
  target_tags   = ["ssh"]
}
```

### ✅ Fixed State
```hcl
variable "developer_ips" {
  type        = list(string)
  description = "List of developer IPs allowed SSH access"
  default     = ["YOUR_IP/32"]  # Replace with your IP: curl ifconfig.me
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "aiwf-allow-ssh"
  network = google_compute_network.aiwf_network.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.developer_ips  # ✅ ONLY YOUR IP
  target_tags   = ["ssh"]
}
```

### Implementation
```bash
# 1. Find your IP
curl ifconfig.me

# 2. Update terraform/variables.tf
# Change: default = ["YOUR_IP/32"]

# 3. Apply
terraform apply -auto-approve
```

**Time: 15 minutes**

---

## Issue #2: SustainBot API Has No Authentication

### 🚨 Current State (INSECURE)
```python
# sustainbot/main.py:45-60
@app.route('/workflows/<name>/execute', methods=['POST'])
def execute_workflow(name):
    """Execute a workflow - NO AUTHENTICATION"""
    data = request.json
    
    # Anyone with network access can execute workflows!
    engine = WorkflowEngine()
    result = engine.execute(name, data)
    return jsonify(result)
```

### ✅ Fixed State
```python
from functools import wraps
import jwt
import os

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return {"error": "Missing Authorization header"}, 401
        
        try:
            token = token.replace('Bearer ', '')
            payload = jwt.decode(
                token,
                os.getenv('JWT_SECRET', 'dev-secret-key'),
                algorithms=['HS256']
            )
            request.user_id = payload['user_id']
            request.actor = payload['actor']
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}, 401
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/workflows/<name>/execute', methods=['POST'])
@require_auth
def execute_workflow(name):
    """Execute workflow - requires JWT token"""
    data = request.json
    
    # Log the actor
    print(f"Executing {name} by {request.actor}")
    
    engine = WorkflowEngine()
    result = engine.execute(name, data)
    return jsonify(result)
```

### Generate Test Token
```python
# In a Python terminal:
import jwt
import json

payload = {
    "user_id": "user123",
    "actor": "jake@sustainnet.io",
    "role": "developer"
}

token = jwt.encode(payload, "dev-secret-key", algorithm="HS256")
print(f"Bearer {token}")

# Use in curl:
# curl -H "Authorization: Bearer <token>" \
#      -X POST http://localhost:5000/workflows/test/execute
```

### Implementation
```bash
# 1. Update sustainbot/main.py with decorator

# 2. Update sustainbot/requirements.txt
# Add: PyJWT==2.10.1

# 3. Update .env
# Add: JWT_SECRET=$(openssl rand -hex 32)

# 4. Test
curl -H "Authorization: Bearer $TOKEN" \
     -X POST http://localhost:5000/workflows/test/execute
```

**Time: 45 minutes**

---

## Issue #3: No Input Validation (Path Traversal Risk)

### 🚨 Current State (INSECURE)
```python
# sustainbot/main.py:60-70
@app.route('/workflows/<name>/execute', methods=['POST'])
def execute_workflow(name):
    """NO VALIDATION - Path traversal possible"""
    
    # Someone could request:
    # /workflows/../../../etc/passwd/execute
    # Or: /workflows/../../secrets.json/execute
    
    engine = WorkflowEngine()
    result = engine.execute(name, data)
    return jsonify(result)
```

### ✅ Fixed State
```python
import re
from pathlib import Path

WORKFLOW_NAMES_REGEX = re.compile(r'^[a-zA-Z0-9_-]+$')
WORKFLOW_DIR = Path('/var/lib/sustainbot/workflows')

def validate_workflow_name(name):
    """Prevent path traversal attacks"""
    if not WORKFLOW_NAMES_REGEX.match(name):
        raise ValueError(f"Invalid workflow name: {name}")
    
    # Check it doesn't escape workflow dir
    workflow_path = (WORKFLOW_DIR / name).resolve()
    if not str(workflow_path).startswith(str(WORKFLOW_DIR.resolve())):
        raise ValueError("Path traversal detected")
    
    return workflow_path

@app.route('/workflows/<name>/execute', methods=['POST'])
@require_auth
def execute_workflow(name):
    """Execute workflow with input validation"""
    try:
        workflow_path = validate_workflow_name(name)
    except ValueError as e:
        return {"error": str(e)}, 400
    
    data = request.json
    engine = WorkflowEngine(workflow_dir=workflow_path)
    result = engine.execute(name, data)
    return jsonify(result)

# Also validate workflow inputs
@app.route('/workflows/<name>/execute', methods=['POST'])
@require_auth
def execute_workflow(name):
    data = request.json
    
    # Validate request body
    if not isinstance(data, dict):
        return {"error": "Request body must be JSON object"}, 400
    
    # Limit input size (1MB max)
    import json
    if len(json.dumps(data)) > 1_000_000:
        return {"error": "Request too large"}, 413
    
    # Validate required fields
    required = ["workflow_name", "parameters"]
    if not all(k in data for k in required):
        return {"error": f"Missing required fields: {required}"}, 400
    
    # Proceed with execution
    workflow_path = validate_workflow_name(name)
    engine = WorkflowEngine(workflow_dir=workflow_path)
    result = engine.execute(name, data)
    return jsonify(result)
```

### Implementation
```bash
# Update sustainbot/main.py with validation functions
# Add to sustainbot/requirements.py if needed
```

**Time: 1 hour**

---

## Issue #4: No Slack Signature Verification

### 🚨 Current State (INSECURE)
```python
# sustainbot/main.py:120-130
@app.route('/slack/events', methods=['POST'])
def slack_events():
    """NO VERIFICATION - Anyone can fake Slack events"""
    
    event = request.json
    
    # This could be from an attacker spoofing Slack!
    if event['type'] == 'slash_command':
        handle_command(event)
    
    return 'OK'
```

### ✅ Fixed State
```python
import hashlib
import hmac
import time
import os

SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET')

def verify_slack_signature(request):
    """Verify request came from Slack"""
    timestamp = request.headers.get('X-Slack-Request-Timestamp')
    signature = request.headers.get('X-Slack-Signature')
    
    # Prevent replay attacks
    if abs(int(time.time()) - int(timestamp)) > 300:  # 5 min window
        raise ValueError("Request timestamp too old")
    
    # Verify signature
    basestring = f"v0:{timestamp}:{request.get_data().decode()}"
    my_signature = f"v0={hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        basestring.encode(),
        hashlib.sha256
    ).hexdigest()}"
    
    if not hmac.compare_digest(my_signature, signature):
        raise ValueError("Invalid signature")

@app.route('/slack/events', methods=['POST'])
def slack_events():
    """Slack webhooks with signature verification"""
    try:
        verify_slack_signature(request)
    except ValueError as e:
        return {"error": str(e)}, 401
    
    event = request.json
    
    # Challenge for URL verification (Slack setup)
    if event.get('type') == 'url_verification':
        return event.get('challenge')
    
    # Handle actual events
    if event.get('type') == 'slash_commands':
        handle_command(event)
    
    return 'OK', 200
```

### Configuration
```bash
# 1. Get Slack signing secret from your app config
# https://api.slack.com/apps/YOUR_APP_ID/general-information

# 2. Add to .env
SLACK_SIGNING_SECRET=your-signing-secret-here

# 3. Set in GitHub Secrets
gh secret set SLACK_SIGNING_SECRET --body "your-signing-secret-here"
```

**Time: 30 minutes**

---

## Issue #5: Insufficient Error Handling

### 🚨 Current State (DANGEROUS)
```python
# sustainbot/main.py:150-160
@app.route('/workflows/<name>/execute', methods=['POST'])
def execute_workflow(name):
    data = request.json
    
    # If anything crashes, user sees internal error details
    engine = WorkflowEngine()
    result = engine.execute(name, data)  # Could expose stack traces
    return jsonify(result)

# Global exception handler missing
# If database fails, user sees raw error
```

### ✅ Fixed State
```python
import logging
from flask import jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SustainBotError(Exception):
    """Base exception for SustainBot"""
    def __init__(self, message, code="INTERNAL_ERROR", http_status=500):
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(self.message)

class WorkflowNotFoundError(SustainBotError):
    def __init__(self, workflow_name):
        super().__init__(
            f"Workflow '{workflow_name}' not found",
            code="WORKFLOW_NOT_FOUND",
            http_status=404
        )

class WorkflowExecutionError(SustainBotError):
    def __init__(self, workflow_name, reason):
        super().__init__(
            f"Failed to execute '{workflow_name}': {reason}",
            code="EXECUTION_FAILED",
            http_status=500
        )

@app.route('/workflows/<name>/execute', methods=['POST'])
@require_auth
def execute_workflow(name):
    """Execute workflow with proper error handling"""
    try:
        # Validate input
        data = request.json
        if not data:
            return {"error": "Empty request body"}, 400
        
        # Validate workflow exists
        workflow_path = validate_workflow_name(name)
        if not workflow_path.exists():
            raise WorkflowNotFoundError(name)
        
        # Execute workflow
        engine = WorkflowEngine(workflow_dir=workflow_path)
        result = engine.execute(name, data)
        
        # Log success
        logger.info(f"Workflow {name} executed successfully by {request.actor}")
        
        return jsonify(result), 200
    
    except SustainBotError as e:
        # Expected error - return user-friendly message
        logger.warning(f"Workflow error: {e.message}")
        return {
            "error": e.message,
            "code": e.code,
            "trace_id": request.headers.get('X-Trace-ID', 'unknown')
        }, e.http_status
    
    except Exception as e:
        # Unexpected error - log but don't expose details
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "trace_id": request.headers.get('X-Trace-ID', 'unknown')
        }, 500

@app.errorhandler(404)
def not_found(error):
    return {
        "error": "Endpoint not found",
        "code": "NOT_FOUND"
    }, 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}", exc_info=True)
    return {
        "error": "Internal server error",
        "code": "INTERNAL_ERROR"
    }, 500
```

**Time: 1 hour**

---

## Implementation Checklist

- [ ] **Fix #1: Restrict SSH** (15 min)
  ```bash
  # In terraform/variables.tf, set your IP
  terraform apply
  ```

- [ ] **Fix #2: Add JWT Auth** (45 min)
  ```bash
  # Update sustainbot/main.py
  # Add PyJWT to requirements.txt
  # Test with generated token
  ```

- [ ] **Fix #3: Input Validation** (1 hour)
  ```bash
  # Add validation functions
  # Test path traversal attempts
  ```

- [ ] **Fix #4: Slack Verification** (30 min)
  ```bash
  # Add signature verification
  # Update .env with signing secret
  ```

- [ ] **Fix #5: Error Handling** (1 hour)
  ```bash
  # Add custom exception classes
  # Add global error handlers
  # Update logging
  ```

---

## Testing Each Fix

### Test SSH Restriction
```bash
# Before fix: Can SSH from anywhere
ssh -i key.json ubuntu@INSTANCE_IP

# After fix: Can only SSH from your IP
# Try from different IP → should timeout
```

### Test JWT Auth
```bash
# Generate token
TOKEN=$(python3 -c "
import jwt
payload = {'user_id': 'test', 'actor': 'test@sustainnet.io'}
print(jwt.encode(payload, 'dev-secret-key', algorithm='HS256'))
")

# Without token → 401
curl http://localhost:5000/workflows/test/execute

# With token → 200
curl -H "Authorization: Bearer $TOKEN" \
     -X POST http://localhost:5000/workflows/test/execute
```

### Test Input Validation
```bash
# Attempt path traversal → should fail
curl -X POST http://localhost:5000/workflows/../etc/passwd/execute

# Valid workflow → should work
curl -X POST http://localhost:5000/workflows/my-workflow/execute
```

### Test Slack Verification
```bash
# Without signature → 401
curl -X POST http://localhost:5000/slack/events \
     -d '{"type": "slash_command"}'

# With valid Slack signature → 200
# (Slack sends valid signature automatically)
```

### Test Error Handling
```bash
# Non-existent workflow
curl http://localhost:5000/workflows/nonexistent/execute
# Returns: 404 with friendly message (not stack trace)

# Invalid JSON
curl -H "Content-Type: application/json" \
     -d "invalid json" \
     http://localhost:5000/workflows/test/execute
# Returns: 400 with friendly message
```

---

## Total Implementation Time

| Fix | Time |
|-----|------|
| SSH restriction | 15 min |
| JWT authentication | 45 min |
| Input validation | 1 hour |
| Slack verification | 30 min |
| Error handling | 1 hour |
| Testing | 1 hour |
| **TOTAL** | **~5 hours** |

---

## After These Fixes

Your security score improves:
- **Before:** 45/100 🚨
- **After:** 70/100 ✅

You can then:
- ✅ Deploy to staging
- ✅ Run integration tests
- ⏳ Plan governance/observability work for production

---

## Next: What to Do

1. **Apply these fixes** (today, ~5 hours)
2. **Test each fix** (1-2 hours)
3. **Deploy to staging** (1 hour)
4. **Verify in staging** (2 hours)
5. **Then tackle AIM-DRAG + observability** for production

---

**Once you apply these fixes, let me know and we'll move to the governance layer. Ready to start?**
