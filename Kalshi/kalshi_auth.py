import os
import base64
import time
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

load_dotenv()

# Load credentials
KALSHI_API_KEY = os.getenv("KALSHI_API_KEY")
raw_key = os.getenv("KALSHI_PRIVATE_KEY")

def get_kalshi_auth_headers(method: str, path: str) -> dict:
    """
    Generates the authentication headers required by Kalshi API v2.
    
    Args:
        method (str): HTTP method (e.g., "GET", "POST").
        path (str): The API path (e.g., "/trade-api/v2/portfolio/balance"). 
                    Must NOT include the host or query parameters.
    """
    # 1. Prepare Timestamp (current time in milliseconds)
    timestamp = str(int(time.time() * 1000))

    # 2. Load Private Key
    # We ensure the key is bytes. If your env var has escaped newlines (e.g. "Line1\nLine2"),
    # you might need to replace them: raw_key.replace('\\n', '\n').encode()
    try:
        private_key = serialization.load_pem_private_key(
            raw_key.encode("utf-8"),
            password=None
        )
    except ValueError:
        raise ValueError("Invalid Private Key format. Ensure it is a valid PEM string.")

    # 3. Construct the Message Payload
    # Format: timestamp + method + path (stripped of query params)
    path_no_query = path.split('?')[0]
    payload = f"{timestamp}{method}{path_no_query}"

    # 4. Sign the Payload using RSA-PSS
    signature = private_key.sign(
        payload.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256()
    )

    # 5. Base64 Encode the Signature
    signature_b64 = base64.b64encode(signature).decode('utf-8')

    # 6. Return Headers
    return {
        "KALSHI-ACCESS-KEY": KALSHI_API_KEY,
        "KALSHI-ACCESS-SIGNATURE": signature_b64,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
        "Content-Type": "application/json"
    }

# --- Usage Example ---
if __name__ == "__main__":
    # Example: getting portfolio balance
    method = "GET"
    endpoint = "/trade-api/v2/portfolio/balance"
    
    try:
        headers = get_kalshi_auth_headers(method, endpoint)
        print("Generated Headers:")
        print(headers)
        
        # You can now use these headers with requests:
        # requests.get("https://api.elections.kalshi.com" + endpoint, headers=headers)
        
    except Exception as e:
        print(f"Error: {e}")