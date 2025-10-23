from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import logging
from typing import Dict, List, Any, Optional
import json
import httpx
from urllib.parse import urlparse

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Environment Variables (BEFORE creating app) ---
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

if not all([GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL]):
    logger.error("Missing required environment variables")
    raise SystemExit("Error: GMAIL_USER, GMAIL_APP_PASSWORD, and RECIPIENT_EMAIL required")

# --- CORS Configuration ---
cors_origins_str = os.getenv("CORS_ORIGINS")
if not cors_origins_str:
    raise SystemExit("Error: CORS_ORIGINS required in .env")
origins = [origin.strip() for origin in cors_origins_str.split(",")]
logger.info(f"CORS origins configured: {origins}")

app = FastAPI(title="Dynamic Form API", version="1.0.0")

# --- Add CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)

# --- Security Configuration ---
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")
ALLOWED_DOMAINS = [d.strip() for d in os.getenv("ALLOWED_DOMAINS", "").split(",")]

if not ALLOWED_DOMAINS or not ALLOWED_DOMAINS[0]:
    raise SystemExit("Error: ALLOWED_DOMAINS required in .env")

logger.info(f"Allowed domains: {ALLOWED_DOMAINS}")

# Determine CAPTCHA provider
captcha_provider = None
if TURNSTILE_SECRET_KEY and RECAPTCHA_SECRET_KEY:
    logger.warning("Both Turnstile and reCAPTCHA configured, using Turnstile")
    captcha_provider = "turnstile"
elif TURNSTILE_SECRET_KEY:
    logger.info("Turnstile CAPTCHA enabled")
    captcha_provider = "turnstile"
elif RECAPTCHA_SECRET_KEY:
    logger.info("reCAPTCHA CAPTCHA enabled")
    captcha_provider = "recaptcha"
else:
    logger.warning("No CAPTCHA configured - not recommended for production")

# --- Pydantic Models ---
class DynamicFormSubmission(BaseModel):
    form_id: str
    data: Dict[str, Any]
    captcha_token: Optional[str] = None
    origin: Optional[str] = None

# --- Forms Database ---
FORMS_DB = {
    "contact": {
        "name": "Contact Form",
        "recipients": ["info@h190k.com"],
        "fields": ["name", "email", "message", "service_type"],
        "template": "contact"
    },
    "support": {
        "name": "Support Form",
        "recipients": ["support@h190k.com"],
        "fields": ["name", "email", "priority", "issue", "description"],
        "template": "support"
    },
    "newsletter": {
        "name": "Newsletter Signup",
        "recipients": ["newsletter@h190k.com"],
        "fields": ["name", "email"],
        "template": "newsletter"
    }
}

# --- Email Templates ---
def get_email_template(form_type: str, data: Dict[str, Any]) -> tuple:
    if form_type == "contact":
        subject = f"New Contact: {data.get('service_type', 'General')}"
        body = f"""
        <h2>New Contact Form Submission</h2>
        <p><strong>Name:</strong> {data.get('name')}</p>
        <p><strong>Email:</strong> {data.get('email')}</p>
        <p><strong>Service Type:</strong> {data.get('service_type')}</p>
        <hr>
        <p><strong>Message:</strong></p>
        <p style="white-space: pre-wrap;">{data.get('message')}</p>
        """
    elif form_type == "support":
        subject = f"Support Ticket - {data.get('priority', 'Normal').upper()}"
        body = f"""
        <h2>New Support Request</h2>
        <p><strong>Name:</strong> {data.get('name')}</p>
        <p><strong>Email:</strong> {data.get('email')}</p>
        <p><strong>Priority:</strong> {data.get('priority')}</p>
        <p><strong>Issue:</strong> {data.get('issue')}</p>
        <hr>
        <p><strong>Description:</strong></p>
        <p style="white-space: pre-wrap;">{data.get('description')}</p>
        """
    elif form_type == "newsletter":
        subject = "New Newsletter Subscriber"
        body = f"""
        <h2>New Newsletter Signup</h2>
        <p><strong>Name:</strong> {data.get('name')}</p>
        <p><strong>Email:</strong> {data.get('email')}</p>
        """
    else:
        subject = "New Form Submission"
        body = f"<h2>Form: {form_type}</h2><pre>{json.dumps(data, indent=2)}</pre>"
    
    return subject, body

# --- Email Sending ---
def send_email(recipients: List[str], subject: str, body: str):
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = GMAIL_USER
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent to {recipients}")
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed")
        raise HTTPException(status_code=500, detail="Email service authentication failed")
    except Exception as e:
        logger.error(f"Email send error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email")

# --- CAPTCHA Verification ---
async def verify_turnstile(token: str) -> bool:
    if not TURNSTILE_SECRET_KEY or not token:
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/validate",
                data={
                    "secret": TURNSTILE_SECRET_KEY,
                    "response": token
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("success", False)
            else:
                logger.error(f"Turnstile API error: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"Turnstile verification error: {e}")
        return False

async def verify_recaptcha(token: str) -> bool:
    if not RECAPTCHA_SECRET_KEY or not token:
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": RECAPTCHA_SECRET_KEY,
                    "response": token
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("success", False)
            else:
                logger.error(f"reCAPTCHA API error: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"reCAPTCHA verification error: {e}")
        return False

# --- Domain Validation ---
def is_domain_allowed(origin: str) -> bool:
    if not origin:
        logger.warning("No origin provided in request")
        return False
    
    try:
        parsed = urlparse(origin)
        # Extract hostname without port (localhost:3000 -> localhost)
        hostname = parsed.hostname or parsed.netloc.split(':')[0]
        hostname = hostname.lower()
        
        allowed = any(
            hostname == allowed_domain.lower() or hostname.endswith(f".{allowed_domain.lower()}")
            for allowed_domain in ALLOWED_DOMAINS
        )
        
        if not allowed:
            logger.warning(f"Domain blocked: {hostname} (origin: {origin})")
        else:
            logger.info(f"Domain allowed: {hostname}")
        return allowed
    except Exception as e:
        logger.error(f"Domain validation error: {e}")
        return False

# --- API Endpoints ---

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Dynamic Form API"}

@app.get("/forms")
def list_forms():
    forms = {}
    for form_id, config in FORMS_DB.items():
        forms[form_id] = {
            "name": config["name"],
            "fields": config["fields"]
        }
    return forms

@app.get("/forms/{form_id}")
def get_form(form_id: str):
    if form_id not in FORMS_DB:
        raise HTTPException(status_code=404, detail="Form not found")
    
    form = FORMS_DB[form_id]
    return {
        "id": form_id,
        "name": form["name"],
        "fields": form["fields"]
    }

@app.options("/{path:path}")
async def options_handler(path: str):
    return {"status": "ok"}

@app.post("/submit/{form_id}", status_code=status.HTTP_200_OK)
async def submit_form(form_id: str, submission: DynamicFormSubmission, request: Request):
    # Domain validation
    origin = submission.origin or request.headers.get("origin", "")
    if not is_domain_allowed(origin):
        raise HTTPException(status_code=403, detail="Origin not allowed")
    
    # CAPTCHA verification (if token provided)
    if submission.captcha_token:
        is_valid = False
        if captcha_provider == "turnstile":
            is_valid = await verify_turnstile(submission.captcha_token)
        elif captcha_provider == "recaptcha":
            is_valid = await verify_recaptcha(submission.captcha_token)
        
        if not is_valid:
            raise HTTPException(status_code=403, detail="CAPTCHA verification failed")
    elif captcha_provider:
        # CAPTCHA is required but no token provided
        raise HTTPException(status_code=400, detail="CAPTCHA token required")
    
    # Form validation
    if form_id not in FORMS_DB:
        raise HTTPException(status_code=404, detail="Form not found")
    
    form_config = FORMS_DB[form_id]
    
    # Required fields check
    for field in form_config["fields"]:
        if field not in submission.data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Send email
    template_type = form_config["template"]
    subject, body = get_email_template(template_type, submission.data)
    
    try:
        send_email(form_config["recipients"], subject, body)
        logger.info(f"Form '{form_id}' submitted successfully from {origin}")
        return {
            "success": True,
            "message": f"Form submitted successfully"
        }
    except Exception as e:
        logger.error(f"Submission error: {e}")
        raise HTTPException(status_code=500, detail="Submission failed")

@app.post("/submit")
async def submit_form_alt(submission: DynamicFormSubmission, request: Request):
    return await submit_form(submission.form_id, submission, request)

@app.on_event("startup")
async def startup():
    logger.info("=" * 50)
    logger.info("Dynamic Form API Started")
    logger.info("=" * 50)
    logger.info("Available forms:")
    for form_id, config in FORMS_DB.items():
        logger.info(f"  • {form_id}: {config['name']}")
    logger.info("=" * 50)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)