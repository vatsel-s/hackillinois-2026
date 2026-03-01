import requests
import json
from kalshi_order_executor import get_kalshi_auth_headers, BASE_URL

def inspect_portfolio():
    """
    Fetches and pretty-prints the raw response from the Kalshi positions endpoint.
    """
    # 1. Define the endpoint
    endpoint = '/trade-api/v2/portfolio/positions'
    full_url = f"{BASE_URL}{endpoint}"

    # 2. Get Headers
    headers = get_kalshi_auth_headers("GET", endpoint)

    # 3. Request & Print
    try:
        print(f"Fetching data from: {full_url} ...\n")
        
        response = requests.get(full_url, headers=headers)
        
        # Check if the request was successful
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            return

        data = response.json()
        
        # 4. Pretty Print the JSON
        print(json.dumps(data, indent=2))

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    inspect_portfolio()