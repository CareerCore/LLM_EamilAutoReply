import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PRODUCTS_CSV = "Data set1.csv"
EMAILS_CSV = "Email_Text data set.csv"