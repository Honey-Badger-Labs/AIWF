#!/bin/bash

# ============================================================================
# Database Initialization Script
# ============================================================================
#
# Initializes the PostgreSQL database for AIWF SustainBot.
# Creates schema, tables, views, triggers, and seed data.
#
# Prerequisites:
#   - PostgreSQL 15+ running
#   - DATABASE_URL configured in .env
#
# Usage:
#   ./scripts/init-database.sh
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# ============================================================================
# STEP 1: Load Environment
# ============================================================================

log_info "Loading environment variables..."

if [ ! -f "$PROJECT_ROOT/.env" ]; then
    log_warning ".env file not found, using .env.example as template"
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    log_warning "Please update .env with your DATABASE_URL before continuing"
    exit 1
fi

# Source .env
export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)

if [ -z "$DATABASE_URL" ]; then
    log_error "DATABASE_URL not set in .env"
    exit 1
fi

log_success "Environment loaded"

# ============================================================================
# STEP 2: Check PostgreSQL Connection
# ============================================================================

log_info "Checking PostgreSQL connection..."

# Extract connection details from DATABASE_URL
# Format: postgresql://user:password@host:port/database
DB_HOST=$(echo $DATABASE_URL | sed -n 's|.*@\(.*\):.*|\1|p')
DB_PORT=$(echo $DATABASE_URL | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo $DATABASE_URL | sed -n 's|.*/\(.*\)$|\1|p')
DB_USER=$(echo $DATABASE_URL | sed -n 's|.*://\(.*\):.*@.*|\1|p')

log_info "Connecting to: $DB_HOST:$DB_PORT/$DB_NAME"

# Test connection
if ! psql "$DATABASE_URL" -c "SELECT 1" &>/dev/null; then
    log_error "Cannot connect to PostgreSQL"
    log_info "Make sure PostgreSQL is running:"
    echo "  docker run -d --name postgres-aiwf -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15"
    exit 1
fi

log_success "PostgreSQL connection OK"

# ============================================================================
# STEP 3: Create Database (if not exists)
# ============================================================================

log_info "Creating database '$DB_NAME' if not exists..."

# Connect to postgres database to create our database
psql postgresql://$DB_USER:$(echo $DATABASE_URL | sed -n 's|.*:\(.*\)@.*|\1|p')@$DB_HOST:$DB_PORT/postgres \
    -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    psql postgresql://$DB_USER:$(echo $DATABASE_URL | sed -n 's|.*:\(.*\)@.*|\1|p')@$DB_HOST:$DB_PORT/postgres \
    -c "CREATE DATABASE $DB_NAME;"

log_success "Database '$DB_NAME' ready"

# ============================================================================
# STEP 4: Run Schema SQL
# ============================================================================

log_info "Running database schema..."

SCHEMA_FILE="$PROJECT_ROOT/database/schema.sql"

if [ ! -f "$SCHEMA_FILE" ]; then
    log_error "Schema file not found: $SCHEMA_FILE"
    exit 1
fi

psql "$DATABASE_URL" -f "$SCHEMA_FILE" &>/dev/null

log_success "Schema created successfully"

# ============================================================================
# STEP 5: Verify Tables Created
# ============================================================================

log_info "Verifying tables created..."

TABLES=$(psql "$DATABASE_URL" -t -c "
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    ORDER BY table_name;
" | grep -v '^$')

log_success "Tables created:"
echo "$TABLES" | while read -r table; do
    echo "  ✓ $table"
done

# ============================================================================
# STEP 6: Verify Views Created
# ============================================================================

log_info "Verifying views created..."

VIEWS=$(psql "$DATABASE_URL" -t -c "
    SELECT table_name 
    FROM information_schema.views 
    WHERE table_schema = 'public' 
    ORDER BY table_name;
" | grep -v '^$')

log_success "Views created:"
echo "$VIEWS" | while read -r view; do
    echo "  ✓ $view"
done

# ============================================================================
# STEP 7: Initialize with SQLAlchemy (optional)
# ============================================================================

log_info "Initializing SQLAlchemy models..."

cd "$PROJECT_ROOT/sustainbot"

python3 -c "
import sys
sys.path.insert(0, '.')
from database import init_database, check_database_health

print('Initializing database...')
init_database(drop_all=False)

print('Checking database health...')
if check_database_health():
    print('✓ Database health check passed')
else:
    print('✗ Database health check failed')
    sys.exit(1)
"

log_success "SQLAlchemy initialization complete"

# ============================================================================
# STEP 8: Display Summary
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_success "DATABASE INITIALIZATION COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Database Summary:"
echo "  Host:     $DB_HOST:$DB_PORT"
echo "  Database: $DB_NAME"
echo "  Tables:   $(echo "$TABLES" | wc -l | xargs)"
echo "  Views:    $(echo "$VIEWS" | wc -l | xargs)"
echo ""
echo "🔗 Connection String:"
echo "  $DATABASE_URL"
echo ""
echo "📖 Next Steps:"
echo "  1. Start Flask server:"
echo "     cd sustainbot && python main.py"
echo ""
echo "  2. Test database health:"
echo "     curl http://localhost:5001/health"
echo ""
echo "  3. View pool status:"
echo "     curl http://localhost:5001/pool-status"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
