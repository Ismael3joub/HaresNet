import sqlite3
import os

DB_PATH = '/home/super/Desktop/New Folder 1/ismael/haresnet.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(domain_filter_group)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'color' not in columns:
            print("Adding color column to domain_filter_group...")
            cursor.execute("ALTER TABLE domain_filter_group ADD COLUMN color VARCHAR(20) DEFAULT '#64748b'")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column 'color' already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
