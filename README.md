# Momentum Python Backend

This is a modular FastAPI backend designed for primary school assessment and quiz management. It implements a layered architecture (Controller/Routes, Services, Repositories, Models, and Schemas) and includes Gemini AI prompts and generator orchestration scripts.

## Installation & Setup

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in any secrets.
   ```bash
   cp .env.example .env
   ```

3. **Run Server**:
   Start the FastAPI development server:
   ```bash
   python app/main.py
   ```
   The application will run on `http://localhost:5000` with interactive API docs at `http://localhost:5000/docs`.
