import os

DB_PASSWORD = os.getenv("DB_PASSWORD", "default_password")
DJANGO_SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "default_key")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "default_twilio_sid")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "default_twilio_token")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "default_twilio_phone")
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID", "default_twilio_service")
gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "default_gmail_password")
gmail_app_email = os.getenv("GMAIL_APP_EMAIL", "default_gmail_email")