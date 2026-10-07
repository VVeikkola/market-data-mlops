import os
import sys
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("TIINGO_API_KEY")

if not api_key:
    print("TIINGO_API_KEY not found in environment variables. Copy .env.example to .env and add your key")
    sys.exit(1)