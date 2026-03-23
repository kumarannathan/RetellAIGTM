curl -X POST http://localhost:5001/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Software Engineer, AI Agents",
    "company": "Retell AI",
    "salary": "$150k - $200k",
    "link": "https://retellai.com/careers"
  }'
