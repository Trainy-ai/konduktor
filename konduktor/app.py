import requests
from datetime import datetime, timedelta

# Prometheus server URL
# url = 'http://localhost:30090/api/v1/query'
url = 'http://localhost:30090/api/v1/query_range'

# Calculate the time range: 1 hour ago to now
end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=1)

# Convert times to RFC3339 format
start_time_str = start_time.isoformat() + 'Z'
end_time_str = end_time.isoformat() + 'Z'

# Parameters for the HTTP GET request
params = {
    'query': 'abs(DCGM_FI_PROF_GR_ENGINE_ACTIVE)',
    'start': start_time_str,
    'end': end_time_str,
    'step': '15s'
}


# Send HTTP GET request to Prometheus
response = requests.get(url, params=params)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()
    print("Query successful!")
    print("Result:", data['data']['result'])
    import pdb; pdb.set_trace()
else:
    print("Failed to retrieve data:", response.status_code, response.text)

