import websockets
import asyncio
from dotenv import load_dotenv
import os
import datetime
import base64
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

load_dotenv()

# 1. Clean up the Key from .env
KALSHI_API_KEY = os.getenv("KALSHI_API_KEY_DEMO")
raw_key = os.getenv("KALSHI_PRIVATE_KEY_DEMO")
if not raw_key:
    print("Error: KALSHI_PRIVATE_KEY_DEMO not found in .env")
    exit()

# Handle potential quoting and escaped newlines
KALSHI_PRIVATE_KEY_STR = raw_key.replace("\\n", "\n").strip('"').strip("'")

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

def load_private_key_from_env(key_string: str):
    return serialization.load_pem_private_key(
        key_string.encode('utf-8'),
        password=None
    )
