# Backend Repository: Developer Onboarding & Setup Guide (Linux/Ubuntu)

Welcome to the **Proctors Backend** repository! This FastAPI application powers the educational assessment platform, AI question compiler, auto-grading engines, and student analytics.

---

## 1. Prerequisites (Ubuntu / Linux)

Ensure the following system packages are installed on your Ubuntu machine:

```bash
# Update APT package list
sudo apt update

# Install Python 3.10+, pip, venv, git, and PostgreSQL client libraries
sudo apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib libpq-dev
```

---

## 2. Environment Configuration

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Configure local variables in `.env`**:
   - `DATABASE_URL`: Defaults to `postgresql://postgres:admin123@localhost:5432/primary_assessment`
   - AI Provider Keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`): Fill in your key(s) for AI features.
   - Development Flags: Keeps `SKIP_EMAIL=true` and `PAUSE_S3=true` for local development.

---

## 3. Database Setup Options

### Option A: Fresh Local Setup & Seed Data (Automated)
Run our automated database setup script from the `backend/` directory:

```bash
chmod +x scripts/setup_db.sh
./scripts/setup_db.sh
```
*Creates local database `primary_assessment`, runs migrations, and seeds default admin (`admin@example.com` / `admin123`) & NCERT curriculum data.*

---

### Option B: Sync Data from Live Render Database
To pull real database tables & data from Render into your local PostgreSQL database:

```bash
chmod +x scripts/sync_db_from_render.sh

# Option 1: Pass Render External Connection String directly
./scripts/sync_db_from_render.sh "postgresql://user:pass@dpg-xxx.oregon-postgres.render.com/proctors_db"

# Option 2: Add RENDER_DATABASE_URL=... to your .env file and run:
./scripts/sync_db_from_render.sh
```

---

## 4. Running the Backend Server (Terminal 1)

With the virtual environment activated, start the FastAPI server:

```bash
# Activate virtual environment
source venv/bin/activate

# Start backend application
python app/main.py
```

The application will run on **`http://localhost:5001`** (or `http://localhost:5000`).

### Interactive API Documentation:
- **Swagger Docs**: `http://localhost:5001/docs`
- **Health Check**: `http://localhost:5001/`

---

## 5. Summary of Default Credentials

- **Admin Portal Email**: `admin@example.com`
- **Admin Portal Password**: `admin123`
- **Database Name**: `primary_assessment`
- **Database User**: `postgres`
- **Database Password**: `admin123`
