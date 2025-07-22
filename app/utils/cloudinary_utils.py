# cloudinary_utils.py
import hashlib
import time
import cloudinary
import os
from dotenv import load_dotenv

load_dotenv()

def init_cloudinary():
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        raise RuntimeError("Cloudinary credentials missing in environment variables")

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )
    

def generate_signature(params: dict) -> str:
    """
    Generate a SHA-1 signature based on Cloudinary upload parameters.
    """
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    if not api_secret:
        raise RuntimeError("Missing CLOUDINARY_API_SECRET in environment variables")

    # Sort parameters alphabetically and build the string to sign
    sorted_params = sorted((k, str(v)) for k, v in params.items())
    to_sign = '&'.join(f'{k}={v}' for k, v in sorted_params)

    # Append secret and hash
    signature = hashlib.sha1((to_sign + api_secret).encode('utf-8')).hexdigest()
    return signature

# Auto-call
init_cloudinary()
