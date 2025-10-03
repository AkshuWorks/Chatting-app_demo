import sqlite3
import logging
from typing import List, Dict, Any, Union

DB_PATH = "messages.db"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def insert_message(data):
    # Required keys for the JSON
    required_keys = {"sender_id", "receiver_id", "message_text"}
    missing_keys = required_keys - data.keys()

    if missing_keys:
        return {"ok": False, "error": f"Missing fields: {', '.join(missing_keys)}"}

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Ensure table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id TEXT NOT NULL,
                    receiver_id TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insert data
            cursor.execute("""
                INSERT INTO messages (sender_id, receiver_id, message_text)
                VALUES (?, ?, ?)
            """, (
                str(data["sender_id"]),
                str(data["receiver_id"]),
                str(data["message_text"])
            ))

            conn.commit()
            message_id = cursor.lastrowid
            return {"message_id": message_id, "status": "success"}

    except sqlite3.IntegrityError as e:
        return {"error": str(e)}, 400

    except Exception as e:
        return {"error": "Database error occurred"}, 500


def fetch_messages(sender_id, receiver_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Select messages where sender and receiver match in either direction
            cursor.execute("""
                SELECT message_id, sender_id, receiver_id, message_text, timestamp
                FROM messages
                WHERE (sender_id = ? AND receiver_id = ?)
                   OR (sender_id = ? AND receiver_id = ?)
                ORDER BY timestamp ASC
            """, (sender_id, receiver_id, receiver_id, sender_id))

            rows = cursor.fetchall()

            messages = [
                {
                    "message_id": row[0],
                    "sender_id": row[1],
                    "receiver_id": row[2],
                    "message_text": row[3],
                    "timestamp": row[4]
                }
                for row in rows
            ]

            if not messages:
                return {"error": "No messages found"}, 404

            return {"messages": messages, "status": "success"}, 200

    except Exception as e:
        return {"error": "Database error occurred"}, 500
