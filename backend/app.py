from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import requests
import os

app = Flask(__name__)

# Configure CORS
CORS(app, origins=[
    "https://chat-frontend.onrender.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
])

# Database server configuration
DB_SERVER = os.environ.get('DATABASE_SERVICE_URL', 'http://localhost:5002')

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s] %(message)s")

# Root route for testing


@app.route("/")
def root():
    return jsonify({"message": "Backend server is running", "status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "API Server"}), 200


@app.route("/message", methods=["POST"])
def send_message():
    try:
        data = request.get_json(force=True)
        logging.info("[API] Received new message request")

        # Validate required fields
        required_fields = ["sender_id", "receiver_id", "message_text"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"'{field}' is required"}), 400

        # Forward request to database server
        response = requests.post(f"{DB_SERVER}/db/insert", json=data)
        return jsonify(response.json()), response.status_code

    except requests.RequestException as e:
        logging.exception("[API] Error connecting to database server")
        return jsonify({"error": "Database service unavailable"}), 503
    except Exception as e:
        logging.exception("[API] Error in POST /message")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route("/messages", methods=["GET"])
def get_messages():
    try:
        sender_id = request.args.get("sender_id")
        receiver_id = request.args.get("receiver_id")

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

        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"'{field}' is required"}), 400

        # Forward request to database server
        response = requests.put(f"{DB_SERVER}/db/update", json=data)
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
        if "message_id" not in data or not data["message_id"]:
            return jsonify({"error": "'message_id' is required"}), 400

        response = requests.delete(f"{DB_SERVER}/db/delete", json=data)
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        logging.exception("[API] Error connecting to database server")
        return jsonify({"error": "Database service unavailable"}), 503
    except Exception as e:
        logging.exception("[API] Error in POST /delete_message")
        return jsonify({"error": "Internal Server Error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting API Server on port {port}...")
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
