import sqlite3
import json
from pathlib import Path

def export_database():
    db_path = Path("output/ai_screen_processor.db")
    if not db_path.exists():
        print(f"Database not found at {db_path.absolute()}!")
        return

    print("Connecting to database...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    export_data = {"sessions": []}
    
    # Fetch all sessions
    sessions = [dict(r) for r in conn.execute("SELECT * FROM sessions ORDER BY id DESC").fetchall()]
    
    for session in sessions:
        session_id = session["id"]
        
        # Fetch timeline (screenshots) for this session
        screenshots = [dict(r) for r in conn.execute("SELECT * FROM screenshots WHERE session_id = ? ORDER BY id ASC", (session_id,)).fetchall()]
        session["timeline"] = screenshots
        
        # Fetch events for this session
        events = [dict(r) for r in conn.execute("SELECT * FROM events WHERE session_id = ? ORDER BY id ASC", (session_id,)).fetchall()]
        session["events"] = events
        
        export_data["sessions"].append(session)

    # Save to JSON
    out_path = Path("output/database_dump.json")
    with open(out_path, "w") as f:
        json.dump(export_data, f, indent=2)
        
    print(f"Successfully exported all database data to: {out_path.absolute()}")

if __name__ == "__main__":
    export_database()
