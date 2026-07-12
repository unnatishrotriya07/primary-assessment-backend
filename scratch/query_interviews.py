import sqlite3
import os

db_path = "test.db"
if not os.path.exists(db_path):
    print("No test.db found.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", [t[0] for t in tables])
    
    # Query recent interviews
    if ("interviews",) in tables or "interviews" in [t[0] for t in tables]:
        cursor.execute("SELECT id, student_name, completed_at FROM interviews ORDER BY id DESC LIMIT 5;")
        rows = cursor.fetchall()
        print("Recent interviews:")
        for r in rows:
            print(f"ID: {r[0]}, Name: {r[1]}, Completed At: {r[2]}")
            
    conn.close()
