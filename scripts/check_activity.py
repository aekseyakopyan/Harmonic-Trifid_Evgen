import urllib.request
import json
import sys

try:
    with urllib.request.urlopen("http://localhost:8000/api/dashboard/recent-activity") as response:
        if response.status != 200:
            print(f"Error: {response.status}")
            sys.exit(1)
        data = json.loads(response.read().decode())
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Exception: {e}")
