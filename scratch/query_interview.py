import psycopg2
import json

db_url = "postgresql://postgres:admin123@localhost:5432/primary_assessment"

try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, student_name, current_question_index, session_state, comfort_index, completion_status, session_state_data 
        FROM interviews 
        WHERE id = 56
    """)
    row = cursor.fetchone()
    if row:
        print("ID:", row[0])
        print("Name:", row[1])
        print("Q Index:", row[2])
        print("Session State:", row[3])
        print("Comfort Index:", row[4])
        print("Completion Status:", row[5])
        print("Session State Data:")
        data = row[6] if row[6] else {}
        print(json.dumps(data, indent=2))
        
        # Also query messages to see transcript
        cursor.execute("""
            SELECT role, text, question_category 
            FROM interview_messages 
            WHERE interview_id = 56 
            ORDER BY id ASC
        """)
        messages = cursor.fetchall()
        print("\nMessages in interview:")
        for m in messages:
            print(f"[{m[0]}] ({m[2]}): {m[1]}")
    else:
        print("Interview 55 not found.")
    conn.close()
except Exception as e:
    print(f"Error querying Postgres: {e}")
