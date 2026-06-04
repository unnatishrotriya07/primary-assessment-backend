import logging
from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database():
    logger.info(f"Connecting to database: {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    # Try adding feedback column to reports table
    with engine.begin() as conn:
        try:
            # We use an ALTER TABLE query which is safe and check if column exists
            # For PostgreSQL, we can use:
            # ALTER TABLE reports ADD COLUMN IF NOT EXISTS feedback VARCHAR;
            # For SQLite, we can just run ALTER TABLE reports ADD COLUMN feedback VARCHAR;
            # (which will error if it already exists, so we catch exception or check first)
            
            # Check if column exists first (db agnostic)
            if "sqlite" in settings.DATABASE_URL.lower():
                # SQLite check
                info = conn.execute(text("PRAGMA table_info(reports)")).fetchall()
                columns = [row[1] for row in info]
                if "feedback" not in columns:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN feedback VARCHAR"))
                    logger.info("Added 'feedback' column to SQLite reports table.")
                else:
                    logger.info("'feedback' column already exists in SQLite reports table.")
            else:
                # PostgreSQL check or general execution
                conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS feedback VARCHAR"))
                logger.info("Executed ALTER TABLE ADD COLUMN IF NOT EXISTS feedback in PostgreSQL.")
                
        except Exception as e:
            logger.error(f"Failed to update table schema: {e}")

if __name__ == "__main__":
    update_database()
