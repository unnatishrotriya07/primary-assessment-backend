#!/usr/bin/env bash
# ==============================================================================
# Momentum Backend - Automated Database & Environment Setup Script (Ubuntu/Linux)
# ==============================================================================
# This script initializes the PostgreSQL database, applies migrations,
# and seeds initial data (Admin user, Default School, NCERT syllabus) for local dev.
# ==============================================================================

set -e

# Terminal formatting colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}  Momentum Backend: Database Setup (Ubuntu / Linux) ${NC}"
echo -e "${BLUE}====================================================${NC}\n"

# 1. Determine script directory and move to backend root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BACKEND_DIR="$( cd "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd )"
cd "$BACKEND_DIR"

# 2. Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[!] .env file not found. Copying .env.example to .env...${NC}"
    cp .env.example .env
    echo -e "${GREEN}[✓] Created .env file.${NC}"
else
    echo -e "${GREEN}[✓] Using existing .env file.${NC}"
fi

# Extract DATABASE_URL from .env or default to local Postgres
DATABASE_URL=$(grep -v '^#' .env | grep DATABASE_URL | cut -d '=' -f2- | tr -d '"' | tr -d "'")
if [ -z "$DATABASE_URL" ]; then
    DATABASE_URL="postgresql://postgres:admin123@localhost:5432/primary_assessment"
fi

echo -e "${BLUE}[i] Configured Database URL: ${DATABASE_URL}${NC}"

# Parse DB credentials from DATABASE_URL if it's PostgreSQL
if [[ "$DATABASE_URL" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASS="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    DB_NAME="${BASH_REMATCH[5]}"
    IS_POSTGRES=true
else
    IS_POSTGRES=false
fi

# 3. Check and setup PostgreSQL database if using Postgres
if [ "$IS_POSTGRES" = true ]; then
    echo -e "\n${BLUE}[1/3] Checking local PostgreSQL service...${NC}"
    
    # Check if pg_isready or systemctl shows postgres running
    if command -v pg_isready >/dev/null 2>&1; then
        if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
            echo -e "${YELLOW}[!] PostgreSQL is not responding on $DB_HOST:$DB_PORT.${NC}"
            echo -e "${YELLOW}[i] Attempting to start postgresql service via systemctl...${NC}"
            sudo systemctl start postgresql || true
        fi
    fi

    echo -e "${BLUE}[2/3] Provisioning PostgreSQL Database '$DB_NAME' and User '$DB_USER'...${NC}"
    
    # Run psql commands as postgres superuser via sudo if needed
    if command -v sudo >/dev/null 2>&1 && id -u postgres >/dev/null 2>&1; then
        sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS' SUPERUSER;"
        
        sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
        
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" >/dev/null 2>&1 || true
        echo -e "${GREEN}[✓] PostgreSQL database and user verified successfully.${NC}"
    else
        # Try direct PGPASSWORD connection
        PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d postgres -c "SELECT 1" >/dev/null 2>&1 || {
            echo -e "${YELLOW}[!] Could not auto-create database as postgres superuser. Ensure database '$DB_NAME' exists.${NC}"
        }
    fi
fi

# 4. Check Virtual Environment & Dependencies
echo -e "\n${BLUE}[3/3] Running Python Schema Migrations & Data Seeding...${NC}"

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}[!] Virtual environment 'venv' not found. Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtualenv
source venv/bin/activate

# Install requirements if pydantic/fastapi not found
if ! python -c "import fastapi" >/dev/null 2>&1; then
    echo -e "${YELLOW}[i] Installing Python dependencies from requirements.txt...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Execute Python database table creation, inline migration, and seeding
echo -e "${BLUE}[i] Creating tables, applying migrations, and seeding default data...${NC}"
python3 -c "
import sys
import os
sys.path.insert(0, os.getcwd())
try:
    import app.main
    print('✅ Database tables created, migrated, and seeded successfully!')
except Exception as e:
    print(f'❌ Error during database setup: {e}')
    sys.exit(1)
"

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}  ✓ Backend Database Setup Complete!                ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "${BLUE}Default Administrator Credentials:${NC}"
echo -e "  - Email:    ${GREEN}admin@example.com${NC}"
echo -e "  - Password: ${GREEN}admin123${NC}"
echo -e "\n${BLUE}To run the backend server now:${NC}"
echo -e "  ${YELLOW}source venv/bin/activate${NC}"
echo -e "  ${YELLOW}python app/main.py${NC}\n"
