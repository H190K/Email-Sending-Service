
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import logging
import asyncio
from contextlib import asynccontextmanager
import threading
import queue

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    logger.info("This is your endpoint: http://0.0.0.0:8000/send")

# --- CORS Middleware ---
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "null"  # Allow requests from file:// URLs
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Data Validation ---
class EmailSchema(BaseModel):
    to_email: EmailStr
    subject: str
    message: str

# --- Environment Variable Loading ---
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD").strip()
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# --- Validation on Startup ---
if not all([GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL]):
    logger.error("Missing one or more critical environment variables: GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL")
    # This will prevent the app from starting if config is missing
    raise SystemExit("Error: Missing critical environment variables. Please check your .env file.")


@app.post("/send", status_code=status.HTTP_200_OK)
async def send_email(email: EmailSchema):
    """
    Endpoint to receive data and send it as an email.
    """
    logger.info(f"Received request to send email to {email.to_email}")

    # --- Email Composition ---
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL  # Always send to the predefined recipient
    msg["Subject"] = email.subject

    # --- Email Body ---
    body = f"""
    You have received a new message from your website contact form.

    --------------------------------------------------
    Recipient: {email.to_email}
    Subject: {email.subject}
    --------------------------------------------------

    Message:
    {email.message}
    """
    msg.attach(MIMEText(body, "plain"))

    # Initiate email sending in background and return immediately
    asyncio.create_task(_send_email_background(msg))
    return {"message": "Email sending initiated"}

@app.get("/")
def read_root():
    return {"message": "Welcome to Email Sending Service API. Use the /send endpoint to send emails."}

# --- Global Connection Pool ---
smtp_pool = queue.Queue(maxsize=5)
_pool_lock = threading.Lock()

# --- Connection Pool Management ---
def create_smtp_connection():
    """Create and return a connected SMTP server object."""
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    return server

@asynccontextmanager
async def get_smtp_connection():
    """Get an SMTP connection from the pool."""
    try:
        # Try to get a connection from the pool with timeout
        connection = smtp_pool.get_nowait()
        logger.debug("Reusing SMTP connection from pool")
        try:
            # Test if connection is still alive
            connection.noop()
            yield connection
        except:
            # Connection is dead, create new one
            logger.debug("Old connection died, creating new one")
            connection = create_smtp_connection()
            yield connection
    except queue.Empty:
        # Pool is empty, create new connection
        logger.debug("Creating new SMTP connection (pool empty)")
        connection = create_smtp_connection()
        yield connection
    finally:
        # Return connection to pool
        try:
            smtp_pool.put_nowait(connection)
            logger.debug("SMTP connection returned to pool")
        except:
            # Pool is full, close the connection
            logger.debug("SMTP pool full, closing connection")
            connection.quit()

async def _send_email_background(msg):
    """Send email in background using connection pooling."""
    try:
        async with get_smtp_connection() as server:
            # Convert to sync for SMTP operations
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, server.send_message, msg)
            logger.info("Email sent successfully!")
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP Authentication Error: Please check your GMAIL_USER and GMAIL_APP_PASSWORD.")
    except Exception as e:
        logger.error(f"Background email sending failed: {e}")

# --- Initialize connection pool on startup ---
@app.on_event("startup")
async def startup_event():
    logger.info("This is your endpoint: http://0.0.0.0:8000/send")
    
    # Pre-populate connection pool
    logger.info("Initializing SMTP connection pool...")
    for _ in range(3):  # Start with 3 connections
        try:
            connection = create_smtp_connection()
            smtp_pool.put(connection)
        except Exception as e:
            logger.warning(f"Failed to create initial pool connection: {e}")
    logger.info(f"SMTP connection pool initialized with {smtp_pool.qsize()} connections")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
