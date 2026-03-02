import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    API_TOKEN = os.getenv("API_TOKEN", "")

settings = Settings()
