import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'json', 'docx', 'pptx'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    RATE_LIMIT = "200 per day, 500 per hour"