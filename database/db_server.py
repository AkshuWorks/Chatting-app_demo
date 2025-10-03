from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Database configuration
DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "messages.db")


# ---------------- INITIALIZE DATABASE ----------------
def init_database():
    """Initialize database directory and table"""
    try:
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
            print(f"[DB] Created database directory: {DB_DIR}")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id TEXT NOT NULL,
                    receiver_id TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print(f"[DB] ✅ Database initialized at: {DB_PATH}")

    except Exception as e:
        print(f"[DB] ❌ Error initializing database: {e}")


# ---------------- PARSE REQUEST DATA ----------------
def parse_request_data(data, required_keys):
    missing_keys = required_keys - data.keys()
    if missing_keys:
        print(f"[DB] ❌ Missing required fields: {', '.join(missing_keys)}")
        return None, f"Missing fields: {', '.join(missing_keys)}"

    extracted = {key: data[key] for key in required_keys}
    print(f"[DB] ✅ Successfully parsed request data: {extracted}")
    return extracted, None


# ---------------- REGISTER FUNCTION ----------------
@app.route("/db/register", methods=["POST"])
def register_user():
    try:
        data = request.get_json(force=True)
        extracted, error = parse_request_data(data, {"user_id", "password"})
        if error:
            return jsonify({"error": error}), 400

        user_id = extracted["user_id"]
        password = extracted["password"]
        print(f"[DB] 📝 Attempting to register user: {user_id}")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )
            """)

            cursor.execute(
                "SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                print(f"[DB] ⚠️ User {user_id} already exists")
                return jsonify({"error": "User already exists"}), 400

            cursor.execute(
                "INSERT INTO users (user_id, password) VALUES (?, ?)", (user_id, password))
            conn.commit()
            print(f"[DB] ✅ User {user_id} registered successfully")
            return jsonify({"status": "success", "user_id": user_id}), 201

    except Exception as e:
        logging.exception("[DB] Error in register_user")
        print(f"[DB] ❌ Error registering user: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


# ---------------- LOGIN FUNCTION ----------------
@app.route("/db/login", methods=["POST"])
def login_user():
    try:
        data = request.get_json(force=True)
        extracted, error = parse_request_data(data, {"user_id", "password"})
        if error:
            return jsonify({"error": error}), 400

        user_id = extracted["user_id"]
        password = extracted["password"]
        print(f"[DB] 🔑 Login attempt for user: {user_id}")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT password FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            if not row:
                print(f"[DB] ⚠️ User {user_id} not found")
                return jsonify({"user_id": False, "password": False}), 200

            password_match = row[0] == password
            print(
                f"[DB] ✅ Login check for {user_id}: password match = {password_match}")
            return jsonify({"user_id": True, "password": password_match}), 200

    except Exception as e:
        logging.exception("[DB] Error in login_user")
        print(f"[DB] ❌ Error during login: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


# ---------------- INSERT MESSAGE ----------------
@app.route("/db/insert", methods=["POST"])
def insert_message():
    try:
        data = request.get_json(force=True)
        logging.info("[DB] Attempting to insert new message")
        logging.debug(f"[DB] Message data: {data}")

        required_keys = {"sender_id", "receiver_id", "message_text"}
        missing_keys = required_keys - data.keys()
        if missing_keys:
            logging.warning(f"[DB] Missing required fields: {missing_keys}")
            return jsonify({"error": f"Missing fields: {', '.join(missing_keys)}"}), 400

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO messages (sender_id, receiver_id, message_text)
                    VALUES (?, ?, ?)
                """, (
                    str(data["sender_id"]),
                    str(data["receiver_id"]),
                    str(data["message_text"])
                ))
                message_id = cursor.lastrowid
                conn.commit()
                print(
                    f"[DB] ✨ Message inserted successfully with ID: {message_id}")
                return jsonify({"message_id": message_id, "status": "success"}), 201

        except sqlite3.IntegrityError as e:
            logging.error(f"[DB] Database integrity error: {e}")
            print(f"[DB] ❌ Database integrity error: {e}")
            return jsonify({"error": str(e)}), 400

        except Exception as e:
            logging.error(f"[DB] Database error: {e}")
            print(f"[DB] ❌ Database error: {e}")
            return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        logging.exception("[DB] Error in insert_message")
        return jsonify({"error": "Internal Server Error"}), 500


# ---------------- FETCH MESSAGE ----------------
@app.route("/db/fetch", methods=["GET"])
def fetch_messages():
    try:
        sender_id = request.args.get("sender_id")
        receiver_id = request.args.get("receiver_id")
        if not sender_id or not receiver_id:
            return jsonify({"error": "sender_id and receiver_id are required"}), 400

        logging.info(
            f"[DB] Fetching messages between {sender_id} and {receiver_id}")
        print(
            f"\n[DB] 🔍 Searching messages between {sender_id} and {receiver_id}")

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT message_id, sender_id, receiver_id, message_text, timestamp
                    FROM messages
                    WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
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
                    print("[DB] 📭 No messages found")
                    return jsonify({"messages": [], "status": "success"}), 200

                print(f"[DB] 📬 Found {len(messages)} messages")
                return jsonify({"messages": messages, "status": "success"}), 200

        except Exception as e:
            logging.error(f"[DB] Error fetching messages: {e}")
            print(f"[DB] ❌ Error fetching messages: {e}")
            return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        logging.exception("[DB] Error in fetch_messages")
        return jsonify({"error": "Internal Server Error"}), 500


# ---------------- DATABASE HEALTH CHECK ----------------
@app.route("/db/health", methods=["GET"])
def db_health_check():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM messages")
            count = cursor.fetchone()[0]
        return jsonify({"status": "healthy", "service": "Database Server", "message_count": count}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "service": "Database Server", "error": str(e)}), 500


# ---------------- DELETE MESSAGE ----------------
@app.route("/db/delete", methods=["DELETE"])
def delete_message():
    try:
        data = request.get_json(force=True)
        parsed, error = parse_request_data(data, {"message_id", "sender_id"})
        if error:
            return jsonify({"error": error}), 400

        message_id = parsed["message_id"]
        sender_id = parsed["sender_id"]
        print(
            f"[DB] 🗑️ Attempting to delete message {message_id} from sender {sender_id}")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM messages
                WHERE message_id = ? AND sender_id = ?
            """, (message_id, sender_id))

            if cursor.rowcount == 0:
                print(
                    f"[DB] ⚠️ Message {message_id} not found or sender mismatch")
                return jsonify({"error": "Message not found or sender mismatch"}), 404

            conn.commit()
            print(f"[DB] ✅ Successfully deleted message {message_id}")
            return jsonify({"status": "success", "deleted_id": message_id}), 200

    except Exception as e:
        logging.exception("[DB] Error deleting message")
        print(f"[DB] ❌ Error deleting message: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


# ---------------- UPDATE MESSAGE ----------------
@app.route("/db/update", methods=["PUT"])
def update_message():
    try:
        data = request.get_json(force=True)
        parsed, error = parse_request_data(
            data, {"message_id", "sender_id", "message_text"})
        if error:
            return jsonify({"error": error}), 400

        message_id = parsed["message_id"]
        sender_id = parsed["sender_id"]
        new_text = parsed["message_text"]
        print(
            f"[DB] ✏️ Attempting to update message {message_id} from sender {sender_id}")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE messages
                SET message_text = ?
                WHERE message_id = ? AND sender_id = ?
            """, (new_text, message_id, sender_id))

            if cursor.rowcount == 0:
                print(
                    f"[DB] ⚠️ Message {message_id} not found or sender mismatch")
                return jsonify({"error": "Message not found or sender mismatch"}), 404

            conn.commit()
            print(f"[DB] ✅ Successfully updated message {message_id}")
            return jsonify({"status": "success", "updated_id": message_id}), 200

    except Exception as e:
        logging.exception("[DB] Error updating message")
        print(f"[DB] ❌ Error updating message: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


if __name__ == "__main__":
    print("Starting Database Server on port 5002...")
    init_database()
    app.run(debug=True, port=5002, use_reloader=False)
