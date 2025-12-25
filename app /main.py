from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# -------------------------
# Platform Meta
# -------------------------
PLATFORM_INFO = {
    "name": "API Platform",
    "status": "active",
    "version": "1.0.0"
}

# -------------------------
# Health Check
# -------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "platform": PLATFORM_INFO["name"],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


# -------------------------
# Public Landing Info
# -------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "platform": PLATFORM_INFO["name"],
        "version": PLATFORM_INFO["version"],
        "message": "A professional platform to list, manage, and sell APIs",
        "endpoints": {
            "/apis": "List available APIs",
            "/subscribe": "Subscribe to an API",
            "/usage": "View API usage",
            "/health": "Platform health status"
        }
    })


# -------------------------
# API Listings (Public)
# -------------------------
@app.route("/apis", methods=["GET"])
def list_apis():
    # Placeholder: APIs will be fetched from database
    return jsonify({
        "total": 0,
        "apis": [],
        "message": "No APIs listed yet"
    })


# -------------------------
# Subscribe to an API
# -------------------------
@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json() or {}

    api_id = data.get("api_id")
    plan = data.get("plan")

    if not api_id or not plan:
        return jsonify({
            "error": "api_id and plan are required"
        }), 400

    return jsonify({
        "status": "pending",
        "api_id": api_id,
        "plan": plan,
        "message": "Subscription request received"
    })


# -------------------------
# API Usage (User)
# -------------------------
@app.route("/usage", methods=["GET"])
def usage():
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return jsonify({
            "error": "API key required"
        }), 401

    return jsonify({
        "api_key": api_key,
        "requests_today": 0,
        "requests_limit": 0,
        "reset_time": "00:00 UTC"
    })


# -------------------------
# Error Handlers
# -------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "error": "Internal server error"
    }), 500


# -------------------------
# Run App
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
