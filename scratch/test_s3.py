import sys
import sqlite3
from sqlalchemy import create_engine, text
from app.core.config import settings

def inspect_db():
    print(f"Inspecting database at URL: {settings.DATABASE_URL}", flush=True)
    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.connect() as conn:
            # List tables
            print("Tables in database:", flush=True)
            if settings.DATABASE_URL.startswith("sqlite"):
                res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            else:
                res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public';"))
            tables = [row[0] for row in res]
            print(tables, flush=True)
            
            # Query schools
            if "schools" in tables:
                print("\nSchool Records:", flush=True)
                schools_res = conn.execute(text("SELECT id, tenant_id, name FROM schools;"))
                for row in schools_res:
                    print(f" - ID: {row[0]}, Tenant ID: {row[1]}, Name: {row[2]}", flush=True)
            
            # Query admins
            if "admins" in tables:
                print("\nAdmin Records (excluding passwords):", flush=True)
                admins_res = conn.execute(text("SELECT id, name, email, role, tenant_id FROM admins;"))
                for row in admins_res:
                    print(f" - ID: {row[0]}, Name: {row[1]}, Email: {row[2]}, Role: {row[3]}, Tenant ID: {row[4]}", flush=True)
                    
    except Exception as e:
        print(f"Failed to inspect database: {e}", flush=True)

if __name__ == "__main__":
    inspect_db()
