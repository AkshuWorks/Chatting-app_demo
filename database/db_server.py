from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import psycopg2
from datetime import datetime
import urllib.parse as urlparse

app = Flask(__name__)

# FIXED: Add proper CORS for your frontend
CORS(app, origins=[
    "https://chat-frontend-vtyj.onrender.com",
    "https://chat-backend-service-fm6k.onrender.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000"
])

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s] %(message)s")

# Database configuration - using Render PostgreSQL


def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')

    print(f"🔍 DATABASE_URL: {database_url}")

    if database_url:
        try:
            # Fix the URL format if needed
            if database_url.startswith('postgresql://'):
                # URL is already correct
                fixed_url = database_url
            elif database_url.startswith('postgres://'):
                # Convert postgres:// to postgresql://
                fixed_url = database_url.replace(
                    'postgres://', 'postgresql://', 1)
            else:
                fixed_url = database_url

            print(f"🔗 Connecting to PostgreSQL: {fixed_url}")

            # Connect using the URL directly
            conn = psycopg2.connect(fixed_url, sslmode='require')
            print("✅ Successfully connected to PostgreSQL")
            return conn

        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            # Don't fall back to SQLite in production - raise the error
            raise Exception(f"PostgreSQL connection failed: {str(e)}")

    # In production, don't fall back to SQLite
    raise Exception("DATABASE_URL environment variable not set")

# ---------------- INITIALIZE DATABASE ----------------


def init_database():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id SERIAL PRIMARY KEY,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                message_text TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database tables initialized successfully")

    except Exception as e:
        print(f"❌ Error initializing database: {e}")

# ---------------- PARSE REQUEST DATA ----------------


def parse_request_data(data, required_keys):
    missing_keys = required_keys - data.keys()
    if missing_keys:
        print(f"[DB] ❌ Missing required fields: {', '.join(missing_keys)}")
        return None, f"Missing fields: {', '.join(missing_keys)}"

    extracted = {key: data[key] for key in required_keys}
    print(f"[DB] ✅ Successfully parsed request data: {extracted}")
    return extracted, None

# ---------------- REGISTER FUNCTION (PostgreSQL) ----------------


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

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if cursor.fetchone():
            print(f"[DB] ⚠️ User {user_id} already exists")
            cursor.close()
            conn.close()
            return jsonify({"error": "User already exists"}), 400

        cursor.execute(
            "INSERT INTO users (user_id, password) VALUES (%s, %s)", (user_id, password))
        conn.commit()
        cursor.close()
        conn.close()

        print(f"[DB] ✅ User {user_id} registered successfully")
        return jsonify({"status": "success", "user_id": user_id}), 201

    except Exception as e:
        logging.exception("[DB] Error in register_user")
        print(f"[DB] ❌ Error registering user: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# ---------------- LOGIN FUNCTION (PostgreSQL) ----------------


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

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM users WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

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

# ---------------- INSERT MESSAGE (PostgreSQL) ----------------


@app.route("/db/insert", methods=["POST"])
def insert_message():
    try:
        data = request.get_json(force=True)
        logging.info("[DB] Attempting to insert new message")

        required_keys = {"sender_id", "receiver_id", "message_text"}
        missing_keys = required_keys - data.keys()
        if missing_keys:
            return jsonify({"error": f"Missing fields: {', '.join(missing_keys)}"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (sender_id, receiver_id, message_text)
            VALUES (%s, %s, %s)
            RETURNING message_id
        """, (data["sender_id"], data["receiver_id"], data["message_text"]))

        message_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        print(f"✨ Message inserted successfully with ID: {message_id}")
        return jsonify({"message_id": message_id, "status": "success"}), 201

    except Exception as e:
        logging.exception("[DB] Error in insert_message")
        return jsonify({"error": "Internal Server Error"}), 500

# ---------------- FETCH MESSAGES (PostgreSQL) ----------------


@app.route("/db/fetch", methods=["GET"])
def fetch_messages():
    try:
        sender_id = request.args.get("sender_id")
        receiver_id = request.args.get("receiver_id")
        if not sender_id or not receiver_id:
            return jsonify({"error": "sender_id and receiver_id are required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT message_id, sender_id, receiver_id, message_text, timestamp
            FROM messages
            WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
            ORDER BY timestamp ASC
        """, (sender_id, receiver_id, receiver_id, sender_id))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        messages = [
            {
                "message_id": row[0],
                "sender_id": row[1],
                "receiver_id": row[2],
                "message_text": row[3],
                "timestamp": row[4].isoformat() if hasattr(row[4], 'isoformat') else row[4]
            }
            for row in rows
        ]

        print(f"📬 Found {len(messages)} messages")
        return jsonify({"messages": messages, "status": "success"}), 200

    except Exception as e:
        logging.exception("[DB] Error in fetch_messages")
        return jsonify({"error": "Internal Server Error"}), 500

# ---------------- UPDATE MESSAGE (PostgreSQL) ----------------


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

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE messages
            SET message_text = %s
            WHERE message_id = %s AND sender_id = %s
        """, (new_text, message_id, sender_id))

        if cursor.rowcount == 0:
            print(f"[DB] ⚠️ Message {message_id} not found or sender mismatch")
            cursor.close()
            conn.close()
            return jsonify({"error": "Message not found or sender mismatch"}), 404

        conn.commit()
        cursor.close()
        conn.close()

        print(f"[DB] ✅ Successfully updated message {message_id}")
        return jsonify({"status": "success", "updated_id": message_id}), 200

    except Exception as e:
        logging.exception("[DB] Error updating message")
        print(f"[DB] ❌ Error updating message: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# ---------------- DELETE MESSAGE (PostgreSQL) ----------------


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

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM messages
            WHERE message_id = %s AND sender_id = %s
        """, (message_id, sender_id))

        if cursor.rowcount == 0:
            print(f"[DB] ⚠️ Message {message_id} not found or sender mismatch")
            cursor.close()
            conn.close()
            return jsonify({"error": "Message not found or sender mismatch"}), 404

        conn.commit()
        cursor.close()
        conn.close()

        print(f"[DB] ✅ Successfully deleted message {message_id}")
        return jsonify({"status": "success", "deleted_id": message_id}), 200

    except Exception as e:
        logging.exception("[DB] Error deleting message")
        print(f"[DB] ❌ Error deleting message: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# ---------------- DATABASE HEALTH CHECK ----------------


@app.route("/db/health", methods=["GET"])
def db_health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({"status": "healthy", "service": "Database Server", "message_count": count}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "service": "Database Server", "error": str(e)}), 500


@app.route("/db/test-connection", methods=["GET"])
def test_connection():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Test a simple query
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM messages")
        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "database": "PostgreSQL",
            "version": version,
            "message_count": count
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "database": "SQLite (fallback)",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    print("Starting Database Server on port 5002...")
    init_database()
    port = int(os.environ.get('PORT', 5002))
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
