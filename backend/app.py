from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database server configuration
DB_SERVER = "http://localhost:5002"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Expected JSON schema
REQUIRED_FIELDS = ["sender_id", "receiver_id", "message_text"]

@app.route("/message", methods=["POST"])
def send_message():
    try:
        data = request.get_json(force=True)
        logging.info("[API] Received new message request")
        logging.debug(f"[API] Incoming POST data: {data}")
        print(f"\n[API] 📨 New message request from {data.get('sender_id')} to {data.get('receiver_id')}")

        # Validate required fields
        for field in REQUIRED_FIELDS:
            if field not in data or not data[field]:
                logging.warning(f"[API] Missing or empty field: {field}")
                return jsonify({"error": f"'{field}' is required"}), 400

        # Forward request to database server
        response = requests.post(f"{DB_SERVER}/db/insert", json=data)
        return jsonify(response.json()), response.status_code

    except requests.RequestException as e:
        logging.exception("[API] Error connecting to database server")
        return jsonify({"error": "Database service unavailable"}), 503
        
    except Exception as e:
        logging.exception("[API] Error in POST /messages")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route("/messages", methods=["GET"])
def get_messages():
    try:
        sender_id = request.args.get("sender_id")
        receiver_id = request.args.get("receiver_id")
        logging.info("[API] Received message fetch request")
        logging.debug(f"[API] GET request params: sender_id={sender_id}, receiver_id={receiver_id}")
        print(f"\n[API] 📬 Fetching messages between {sender_id} and {receiver_id}")

        if not sender_id or not receiver_id:
            return jsonify({"error": "sender_id and receiver_id are required"}), 400

        # Forward request to database server
        response = requests.get(
            f"{DB_SERVER}/db/fetch",
            params={"sender_id": sender_id, "receiver_id": receiver_id}
        )
        return jsonify(response.json()), response.status_code

    except requests.RequestException as e:
        logging.exception("[API] Error connecting to database server")
        return jsonify({"error": "Database service unavailable"}), 503

    except Exception as e:
        logging.exception("[API] Error in GET /messages")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/edit_message", methods=["POST"])
def edit_message():
    try:
        data = request.get_json(force=True)
        required_fields = ["message_id", "sender_id", "message_text"]
        
        # Validate required fields
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"'{field}' is required"}), 400
                
        # Rest of the code...
        logging.info("[API] Received edit message request")
        logging.debug(f"[API] Incoming POST data for edit: {data}")
        print(f"\n[API] ✏️ Edit message request for message ID: {data.get('message_id')}")
        if "message_id" not in data or not data["message_id"]:
            return jsonify({"error": "'message_id' is required"}), 400
        
        # Forward request to database server
        response = requests.put(f"{DB_SERVER}/db/edit", json=data)
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logging.exception("[API] Error connecting to database server")
        return jsonify({"error": "Database service unavailable"}), 503
    except Exception as e:
        logging.exception("[API] Error in POST /edit_message")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/delete_message", methods=["POST"])
def delete_message():
    try:
        data = request.get_json(force=True)
        logging.info("[API] Received delete message request")
        logging.debug(f"[API] Incoming POST data for delete: {data}")
        print(f"\n[API] 🗑️ Delete message request for message ID: {data.get('message_id')}")
        if "message_id" not in data or not data["message_id"]:
            return jsonify({"error": "'message_id' is required"}), 400

        # Forward request to database server
        response = requests.delete(f"{DB_SERVER}/db/delete", json=data)
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logging.exception("[API] Error connecting to database server")
        return jsonify({"error": "Database service unavailable"}), 503
    except Exception as e:
        logging.exception("[API] Error in POST /delete_message")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "API Server"}), 200


if __name__ == "__main__":
    print("Starting API Server on port 5001...")
    app.run(debug=True, port=5001, use_reloader=False)