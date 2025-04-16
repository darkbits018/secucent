import json
from db.connection import get_db_connection


def fetch_guides():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, guide_data FROM guides")
    guides = cursor.fetchall()
    cursor.close()
    conn.close()
    return guides


def debug_guide_structure(guide_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT guide_data FROM guides WHERE id = %s", (guide_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        print(f"\n📦 Raw guide_data for ID {guide_id}:\n")
        try:
            guide_json = json.loads(row['guide_data'])
            print(json.dumps(guide_json, indent=2)[:2000])
        except Exception as e:
            print("❌ Failed to parse guide_data:", e)
    else:
        print("❌ Guide not found.")
