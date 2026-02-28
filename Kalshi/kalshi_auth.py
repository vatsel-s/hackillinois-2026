# kalshi_auth.py
import os
import base64
import datetime
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

load_dotenv()

KALSHI_API_KEY = os.getenv("KALSHI_API_KEY")
raw_key = os.getenv("KALSHI_PRIVATE_KEY")

if not KALSHI_API_KEY:
    raise EnvironmentError("Error: KALSHI_API_KEY not found in .env")
if not raw_key:
    raise EnvironmentError("Error: KALSHI_PRIVATE_KEY not found in .env")

KALSHI_PRIVATE_KEY_STR = raw_key.replace("\\n", "\n").strip('"').strip("'")

def load_private_key_from_env(key_string: str) -> rsa.RSAPrivateKey:
    return serialization.load_pem_private_key(
        key_string.encode('utf-8'),
        password=None
    )

def sign_pss_text(private_key: rsa.RSAPrivateKey, text: str) -> str:
    message = text.encode('utf-8')
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def build_auth_headers(method: str, path: str) -> dict:
    """Helper to generate fresh auth headers for any request."""
    timestamp = str(int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000))
    msg = timestamp + method + path
    priv_key = load_private_key_from_env(KALSHI_PRIVATE_KEY_STR)
    return {
        "KALSHI-ACCESS-KEY": KALSHI_API_KEY,
        "KALSHI-ACCESS-SIGNATURE": sign_pss_text(priv_key, msg),
        "KALSHI-ACCESS-TIMESTAMP": timestamp
    }