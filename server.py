import os
import json
import time
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Retell AI Proxy
@app.route('/proxy/create-phone-call', methods=['POST'])
def proxy_retell():
    api_key = request.headers.get('Authorization')
    if not api_key:
        return jsonify({"error": "No API key provided"}), 401
    
    url = "https://api.retellai.com/create-phone-call"
    try:
        response = requests.post(url, json=request.json, headers={"Authorization": api_key})
        return (response.content, response.status_code, response.headers.items())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Apollo Search Proxy
@app.route('/proxy/apollo/search', methods=['POST'])
def proxy_apollo():
    api_key = request.headers.get('X-Apollo-Key')
    if not api_key:
        return jsonify({"error": "No Apollo API key provided"}), 401
    
    url = "https://api.apollo.io/v1/mixed_people/search"
    try:
        # Apollo expects the API key in the body or header depending on version, 
        # but usually it's x-api-key or in the body.
        # The frontend sends 'X-Apollo-Key'.
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache"
        }
        # Apollo API usually takes api_key in the body
        data = request.json
        data['api_key'] = api_key
        
        response = requests.post(url, json=data, headers=headers)
        return (response.content, response.status_code, response.headers.items())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Real-time Activity Stream (SSE)
@app.route('/stream')
def stream():
    def event_stream():
        # Simulated activity for demonstration
        activities = [
            {"timestamp": "1m ago", "channel": "Inbound", "outcome": "Demo booked", "call_id": "call_123"},
            {"timestamp": "5m ago", "channel": "Outbound", "outcome": "Voicemail", "call_id": "call_456"},
            {"timestamp": "12m ago", "channel": "Retell AI", "outcome": "Connected", "call_id": "call_789"}
        ]
        import random
        while True:
            time.sleep(10)  # Send an update every 10 seconds
            activity = random.choice(activities)
            activity['timestamp'] = "Just now"
            yield f"data: {json.dumps(activity)}\n\n"
            
    return Response(event_stream(), mimetype="text/event-stream")

# Serve the frontend
@app.route('/')
def home():
    return open('index.html').read()

if __name__ == '__main__':
    # Running on port 5001 as expected by index.html
    print("Dashboard listening at http://localhost:5001")
    app.run(port=5001, debug=True)
