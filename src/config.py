import os
from dotenv import load_dotenv

load_dotenv()

AIMLAPI_KEY = os.getenv("AIMLAPI_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "bagoodex/bagoodex-search-v1")
MAX_TOKENS = int(os.getenv("MODEL_MAX_TOKENS", "200"))
BASE_URL = os.getenv("BASE_URL", "https://api.aimlapi.com")
