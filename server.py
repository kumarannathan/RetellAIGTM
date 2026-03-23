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
JOBS_FILE = 'jobs.json'

def init_jobs_file():
    if not os.path.exists(JOBS_FILE):
        with open(JOBS_FILE, 'w') as f:
            json.dump([], f)

init_jobs_file()

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    try:
        with open(JOBS_FILE, 'r') as f:
            jobs = json.load(f)
        return jsonify(jobs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/jobs', methods=['POST'])
def add_job():
    try:
        data = request.json
        # Expecting title, date, salary, company, link
        required_fields = ['title', 'company', 'link']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
                
        # Fill in optional fields with empty strings if missing
        job_entry = {
            "id": str(int(time.time() * 1000)),
            "title": data.get("title", ""),
            "date": data.get("date", ""),
            "salary": data.get("salary", ""),
            "company": data.get("company", ""),
            "link": data.get("link", "")
        }
        
        with open(JOBS_FILE, 'r') as f:
            jobs = json.load(f)
            
        jobs.insert(0, job_entry) # Add to the top
        
        with open(JOBS_FILE, 'w') as f:
            json.dump(jobs, f, indent=2)
            
        return jsonify({"message": "Job added successfully", "job": job_entry}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

# --- JSEARCH ENDPOINTS FOR CLAWDBOT ---
JSEARCH_API_KEY = "658204ac81msh00f29a23afa6fc3p18f576jsn088e26849052"
JSEARCH_HOST = "jsearch.p.rapidapi.com"

@app.route('/api/bot/jsearch', methods=['POST'])
def bot_jsearch():
    try:
        data = request.json or {}
        # default to what the user indicated: relevant to cs new grad
        query = data.get("query", "software engineer new grad OR computer science new grad")
        
        # 1. Search JSearch
        url = f"https://{JSEARCH_HOST}/search"
        querystring = {"query": query, "page": "1", "num_pages": "1"}
        headers = {
            "x-rapidapi-host": JSEARCH_HOST,
            "x-rapidapi-key": JSEARCH_API_KEY
        }
        
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        response_data = response.json()
        
        if "data" not in response_data:
            return jsonify({"error": "Failed to fetch from JSearch", "details": response_data}), 500
            
        jobs_added = []
        memory_lines = []
        
        with open(JOBS_FILE, 'r') as f:
            existing_jobs = json.load(f)
            
        for job in response_data["data"][:5]: # Take top 5 results
            title = job.get("job_title", "")
            company = job.get("employer_name", "")
            
            salary_text = ""
            if job.get('job_min_salary') and job.get('job_max_salary'):
                salary_text = f"${job['job_min_salary']} - ${job['job_max_salary']}"
            else:
                try:
                    # Fallback to estimated salary API
                    sl_url = f"https://{JSEARCH_HOST}/estimated-salary"
                    sl_query = {"job_title": title, "location": job.get("job_location", "USA"), "radius": "100"}
                    # Adding a timeout and short sleep to prevent rate limiting
                    time.sleep(1)
                    sl_res = requests.get(sl_url, headers=headers, params=sl_query, timeout=5).json()
                    if "data" in sl_res and len(sl_res["data"]) > 0:
                        est = sl_res["data"][0]
                        salary_text = f"Est: ${est.get('min_salary', '')} - ${est.get('max_salary', '')}"
                except:
                    pass
            
            link = job.get("job_apply_link", "") or job.get("job_google_link", "")
            job_date = job.get("job_posted_at_datetime_utc", "")
            
            job_entry = {
                "id": str(int(time.time() * 1000)) + str(len(jobs_added)),
                "title": title,
                "date": job_date[:10] if job_date else time.strftime("%Y-%m-%d"),
                "salary": salary_text,
                "company": company,
                "link": link
            }
            jobs_added.append(job_entry)
            existing_jobs.insert(0, job_entry)
            
            # format for memory.md
            memory_lines.append(f"- **{title}** at {company}")
            memory_lines.append(f"  Link: {link}")
            if salary_text:
                memory_lines.append(f"  Salary: {salary_text}")
                
        # Write back to jobs.json
        with open(JOBS_FILE, 'w') as f:
            json.dump(existing_jobs, f, indent=2)
            
        # Append to memory.md
        with open("memory.md", "a") as f:
            f.write(f"\n## Bot Job Search ({time.strftime('%Y-%m-%d %H:%M:%S')})\n")
            f.write(f"Query: {query}\n\n")
            f.write("\n".join(memory_lines) + "\n")
            
        return jsonify({"message": f"Successfully added {len(jobs_added)} jobs", "jobs": jobs_added}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bot/jsearch/job-details', methods=['GET'])
def proxy_jsearch_details():
    job_id = request.args.get('job_id')
    url = f"https://{JSEARCH_HOST}/job-details"
    headers = {
        "x-rapidapi-host": JSEARCH_HOST,
        "x-rapidapi-key": JSEARCH_API_KEY
    }
    res = requests.get(url, headers=headers, params={"job_id": job_id})
    return (res.content, res.status_code, res.headers.items())

@app.route('/api/bot/jsearch/estimated-salary', methods=['GET'])
def proxy_jsearch_salary():
    url = f"https://{JSEARCH_HOST}/estimated-salary"
    headers = {
        "x-rapidapi-host": JSEARCH_HOST,
        "x-rapidapi-key": JSEARCH_API_KEY
    }
    res = requests.get(url, headers=headers, params=request.args)
    return (res.content, res.status_code, res.headers.items())


# Serve the frontend
@app.route('/')
def home():
    return open('index.html').read()

if __name__ == '__main__':
    # Running on port 5001 as expected by index.html
    print("Dashboard listening at http://localhost:5001")
    app.run(port=5001, debug=True)
