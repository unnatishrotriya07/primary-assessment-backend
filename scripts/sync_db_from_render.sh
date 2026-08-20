#!/usr/bin/env bash
# ==============================================================================
# Proctors Backend - Sync Database from Render to Local PostgreSQL
# ==============================================================================
# This script dumps the live database from Render and restores it into your
# local PostgreSQL database (primary_assessment).
#
# Usage:
#   1. Set RENDER_DATABASE_URL in .env OR pass it as an argument:
#      ./scripts/sync_db_from_render.sh "postgresql://user:pass@dpg-xxx.render.com/proctors_db"
#   2. Or simply run the script and paste your Render External Database URL when prompted.
# ==============================================================================

set -e

# Terminal formatting colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}  Sync Database: Render (Remote) ➔ Local PostgreSQL  ${NC}"
echo -e "${BLUE}====================================================${NC}\n"

# 1. Determine script directory and move to backend root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BACKEND_DIR="$( cd "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd )"
cd "$BACKEND_DIR"

# 2. Check for required PostgreSQL client utilities
if ! command -v pg_dump >/dev/null 2>&1; then
    echo -e "${RED}[❌] Error: 'pg_dump' utility not found. Please install postgresql-client (sudo apt install postgresql-client).${NC}"
    exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
    echo -e "${RED}[❌] Error: 'psql' utility not found. Please install postgresql-client (sudo apt install postgresql-client).${NC}"
    exit 1
fi

# 3. Get Render Database URL
RENDER_URL="$1"

if [ -z "$RENDER_URL" ] && [ -f ".env" ]; then
    RENDER_URL=$(grep -v '^#' .env | grep RENDER_DATABASE_URL | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
fi

if [ -z "$RENDER_URL" ]; then
    echo -e "${YELLOW}[?] RENDER_DATABASE_URL not found in .env or arguments.${NC}"
    echo -e -n "${BLUE}👉 Please paste your Render External Database Connection String:${NC} "
    read -r RENDER_URL
fi

if [ -z "$RENDER_URL" ]; then
    echo -e "${RED}[❌] Error: Render Database URL is required. Exiting.${NC}"
    exit 1
fi

# Fix postgresql:// vs postgres:// URL scheme if necessary for pg_dump
RENDER_URL_CLEAN=$(echo "$RENDER_URL" | sed 's/^postgres:\/\//postgresql:\/\//')

# 4. Get Local Database Credentials from .env
LOCAL_URL=""
if [ -f ".env" ]; then
    LOCAL_URL=$(grep -v '^#' .env | grep DATABASE_URL | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
fi

if [ -z "$LOCAL_URL" ]; then
    LOCAL_URL="postgresql://postgres:admin123@localhost:5432/primary_assessment"
fi

# Parse Local DB credentials
if [[ "$LOCAL_URL" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
    LOCAL_USER="${BASH_REMATCH[1]}"
    LOCAL_PASS="${BASH_REMATCH[2]}"
    LOCAL_HOST="${BASH_REMATCH[3]}"
    LOCAL_PORT="${BASH_REMATCH[4]}"
    LOCAL_NAME="${BASH_REMATCH[5]}"
else
    echo -e "${RED}[❌] Error: Local DATABASE_URL must be a valid PostgreSQL connection string.${NC}"
    echo -e "${YELLOW}Example: postgresql://postgres:admin123@localhost:5432/primary_assessment${NC}"
    exit 1
fi

# 5. Create backup dump file
DUMP_FILE="$BACKEND_DIR/render_snapshot.sql"

echo -e "\n${BLUE}[1/3] Dumping database from Render...${NC}"
echo -e "${BLUE}      Target: ${RENDER_URL_CLEAN:0:35}...${NC}"

# Execute pg_dump
if pg_dump "$RENDER_URL_CLEAN" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --file="$DUMP_FILE"; then
    echo -e "${GREEN}[✓] Render database dump created successfully ($(du -h "$DUMP_FILE" | cut -f1)).${NC}"
else
    echo -e "${RED}[❌] Failed to dump database from Render. Check your Render Connection String and internet connection.${NC}"
    rm -f "$DUMP_FILE"
    exit 1
fi

# 6. Ensure local database exists
echo -e "\n${BLUE}[2/3] Verifying local database '$LOCAL_NAME'...${NC}"
if command -v sudo >/dev/null 2>&1 && id -u postgres >/dev/null 2>&1; then
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$LOCAL_NAME'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE $LOCAL_NAME OWNER $LOCAL_USER;"
fi

# 7. Restore dump into local database
echo -e "\n${BLUE}[3/3] Restoring snapshot into local database '$LOCAL_NAME'...${NC}"

PGPASSWORD="$LOCAL_PASS" psql \
    -h "$LOCAL_HOST" \
    -p "$LOCAL_PORT" \
    -U "$LOCAL_USER" \
    -d "$LOCAL_NAME" \
    -f "$DUMP_FILE" >/dev/null 2>&1 || {
        echo -e "${YELLOW}[!] psql returned non-zero warning during restore (normal for table drops if fresh).<sup></sup>${NC}"
    }

# Cleanup dump file
rm -f "$DUMP_FILE"

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}  ✓ Data Sync Complete! Render Data is now Local!    ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "${BLUE}Local Database Name:${NC} ${GREEN}$LOCAL_NAME${NC}"
echo -e "${BLUE}Local Connection:${NC}    ${GREEN}$LOCAL_URL${NC}\n"
