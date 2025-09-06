# Email Sending Service

This project provides a simple backend service using FastAPI to send emails and a basic HTML form to interact with it.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/H190K/Email-Sending-Service
cd Email-Sending-Service
```

### 2. Create and Configure the `.env` file

Create a file named `.env` in the root directory of the project with the following content:

```
GMAIL_USER=your_gmail_address@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
RECIPIENT_EMAIL=recipient_email_address@example.com
```

**Important:**
- `GMAIL_USER`: Your Gmail address.
- `GMAIL_APP_PASSWORD`: You need to generate an App Password for your Gmail account. Follow these steps:
    1. Enable 2-Step Verification for your Google Account if you haven't already.
    2. Go to your Google Account Security page: [https://myaccount.google.com/security](https://myaccount.google.com/security)
    3. Under "How you sign in to Google", select "App passwords". You might need to sign in.
    4. At the bottom, choose "Mail" and "Other (Custom name)" and enter a name like "Email Sending Service".
    5. Click "Generate". A 16-character password will appear in the yellow bar. This is your App Password.
    6. Copy this password and paste it into your `.env` file.
- `RECIPIENT_EMAIL`: The email address where you want to receive the messages from the form.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the FastAPI Application

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The application will start, and you will see the endpoint URL in the console (e.g., `http://0.0.0.0:8000/send`).

## HTML Form Setup

To use this service with an HTML form, you can use JavaScript to send a POST request to the `/send` endpoint.

You can use the included [`index.html`](https://github.com/h190k/Email-Sending-Service/blob/main/index.html) to test the email sending functionality.


**Key points for the HTML form:**

- **Form Fields**: Ensure your form has input fields with these exact `name` attributes:
  - `to_email`: Sender's email address (required)
  - `subject`: Email subject line (required) 
  - `message`: Email body content (required)

These field names must match exactly as they are used in the backend handler.
- **JavaScript**: The `<script>` block handles the form submission:
    - It prevents the default form submission.
    - Gathers data from the form fields.
    - Sends a `POST` request to the `/send` endpoint with the form data as a JSON payload.
    - Displays success or error messages based on the server's response.
- **Endpoint URL**: The included `index.html` uses `http://127.0.0.1:8000/send`. Make sure to replace this in the JavaScript `fetch` call with the actual endpoint URL displayed in your console when you run the FastAPI application.

### Performance Optimizations

The email sending system has been optimized for performance and scalability:

1. **Asynchronous Processing**: Email sending happens in the background using `asyncio`, allowing the API to respond immediately instead of waiting for email transmission.
2. **Connection Pooling**: SMTP connections are reused and managed through a connection pool, significantly reducing overhead and connection latency.
3. **Background Workers**: Multiple emails can be processed concurrently without blocking the API response.
4. **Quick Response Time**: The system typically handles emails 5-10x faster than the previous implementation.

**Note on Endpoint Behavior:**
The `/send` endpoint now returns immediately with a success message like `{"message": "Email sending initiated"}` rather than waiting for the email to be fully transmitted. This provides better user experience, though it means successful delivery confirmation is no longer immediate.

**Technical Implementation:**
The system uses:
- `asyncio` for non-blocking background tasks
- `queue.Queue` for efficient connection pooling
- `contextlib.asynccontextmanager` for safe connection management
- Automatic connection health checking and reconnection

This optimized architecture ensures smooth handling of multiple email requests while maintaining system responsiveness.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

**💖 Support the Project:**
If you find my projects useful, consider supporting me with a donation.  
Your support helps me create more open-source tools and share them with the community.  

[![Donate on DeStream](https://img.shields.io/badge/Donate-DeStream-blue?style=for-the-badge)](https://destream.net/live/H190K/donate)  
[![Donate with NOWPayments](https://img.shields.io/badge/Donate-NOWPayments-purple?style=for-the-badge)](https://nowpayments.io/donation?api_key=J0QACAH-BTH4F4F-QDXM4ZS-RCA58BH)