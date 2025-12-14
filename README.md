# Dynamic Form Email Service

[![Python Version](https://img.shields.io/badge/python-3.8+-blue?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-H190K/Email--Sending--Service-black?style=flat-square&logo=github)](https://github.com/H190K/Email-Sending-Service)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=flat-square)]()

A production-ready FastAPI backend service for handling multiple dynamic forms with email forwarding, CAPTCHA verification, and domain whitelisting.

## Features

- **Multiple Forms**: Support for unlimited dynamic forms (contact, support, newsletter, etc.)
- **Email Forwarding**: Sends form submissions directly to your inbox via Gmail
- **CAPTCHA Protection**: Optional Turnstile or reCAPTCHA verification
- **Domain Whitelisting**: Only accept submissions from authorized domains
- **CORS Protection**: Configure which origins can access the API
- **Production Ready**: Proper error handling, logging, and security

## Prerequisites

- Python 3.8+
- Gmail account with 2-Factor Authentication enabled
- (Optional) Turnstile or reCAPTCHA account for CAPTCHA

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/H190K/Email-Fetching-Service
cd Email-Sending-Service
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create and Configure `.env` File

Create a `.env` file in the root directory:

```env
# Email Configuration
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
RECIPIENT_EMAIL=where@to.send

# CORS & Security (required)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ALLOWED_DOMAINS=yourdomain.com,www.yourdomain.com

# CAPTCHA - Choose ONE (optional but recommended for production)

# Option 1: Turnstile (Cloudflare - recommended)
# Get from: https://dash.cloudflare.com → Turnstile
TURNSTILE_SECRET_KEY=your_turnstile_secret_key_here

# Option 2: reCAPTCHA (Google)
# Get from: https://www.google.com/recaptcha/admin
 RECAPTCHA_SECRET_KEY=your_recaptcha_secret_key_here
```

### 4. Get Gmail App Password

Since you're using Gmail:

1. Enable 2-Step Verification on your Google Account if not already enabled
2. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
3. Find "App passwords" under "How you sign in to Google"
4. Select **Mail** and **Windows Computer** (or your OS)
5. Google will generate a 16-character password
6. Copy this password to your `.env` file as `GMAIL_APP_PASSWORD`

**Important**: Use the App Password, NOT your Gmail password.

### 5. (Optional) Set Up CAPTCHA

#### Turnstile (Recommended)

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → **Turnstile**
2. Click **Create Site**
3. Enter your domain and select **Managed Mode**
4. Copy the **Secret Key** to your `.env`

#### reCAPTCHA

1. Go to [google.com/recaptcha/admin](https://www.google.com/recaptcha/admin)
2. Create a new reCAPTCHA v3 site
3. Copy the **Secret Key** to your `.env`

### 6. Run the Application

```bash
python main.py
```

The API will start at `http://0.0.0.0:8000`

## API Endpoints

### Health Check
```
GET /
Response: {"status": "ok", "service": "Dynamic Form API"}
```

### List Available Forms
```
GET /forms
Response: {
  "contact": {
    "name": "Contact Form",
    "fields": ["name", "email", "message", "service_type"]
  },
  ...
}
```

### Get Form Details
```
GET /forms/{form_id}
```

### Submit Form
```
POST /submit/{form_id}
Content-Type: application/json

{
  "form_id": "contact",
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Hello",
    "service_type": "support"
  },
  "captcha_token": "token_from_turnstile_or_recaptcha",
  "origin": "https://yourdomain.com"
}
```

## HTML Form Integration

### Basic Example

```html
<form id="contactForm">
  <input type="text" id="name" placeholder="Your Name" required>
  <input type="email" id="email" placeholder="Your Email" required>
  <select id="service_type" required>
    <option value="">Select Service</option>
    <option value="support">Support</option>
    <option value="sales">Sales</option>
  </select>
  <textarea id="message" placeholder="Your Message" required></textarea>
  <button type="submit">Send</button>
</form>

<script>
document.getElementById('contactForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const data = {
    form_id: 'contact',
    data: {
      name: document.getElementById('name').value,
      email: document.getElementById('email').value,
      service_type: document.getElementById('service_type').value,
      message: document.getElementById('message').value
    },
    origin: window.location.origin
  };
  
  const response = await fetch('https://your-api-domain.com/submit/contact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  const result = await response.json();
  if (result.success) {
    alert('Form submitted!');
  } else {
    alert('Error: ' + result.detail);
  }
});
</script>
```

### With Turnstile CAPTCHA

Add to your HTML `<head>`:
```html
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
```

Add to your form:
```html
<div class="cf-turnstile" data-sitekey="YOUR_SITE_KEY"></div>
```

Then in your JavaScript:
```javascript
const token = document.querySelector('[name="cf-turnstile-response"]')?.value;

const data = {
  form_id: 'contact',
  data: { ... },
  captcha_token: token,
  origin: window.location.origin
};
```

## Adding New Forms

Edit `app.py` and add to `FORMS_DB`:

```python
FORMS_DB = {
  "my_new_form": {
    "name": "My New Form",
    "recipients": ["email@example.com"],
    "fields": ["name", "email", "custom_field"],
    "template": "custom"
  },
  ...
}
```

Then add the email template in `get_email_template()`:

```python
elif form_type == "custom":
  subject = "New Custom Submission"
  body = f"""
  <h2>New Submission</h2>
  <p><strong>Name:</strong> {data.get('name')}</p>
  <p><strong>Custom Field:</strong> {data.get('custom_field')}</p>
  """
```

## Local Development

For local testing without CAPTCHA:

```env
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
RECIPIENT_EMAIL=your_email@gmail.com
CORS_ORIGINS=http://localhost,http://localhost:3000,http://127.0.0.1
ALLOWED_DOMAINS=localhost,127.0.0.1
# Leave CAPTCHA keys empty
```

## Deployment

### Railway, Render, or Heroku

1. Push code to GitHub
2. Connect repository to your hosting platform
3. Set environment variables in platform dashboard
4. Deploy

### Environment Variables in Production

Set these in your hosting platform's environment variables section:
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`
- `RECIPIENT_EMAIL`
- `CORS_ORIGINS`
- `ALLOWED_DOMAINS`
- `TURNSTILE_SECRET_KEY` (optional)
- `RECAPTCHA_SECRET_KEY` (optional)

## Security Best Practices

- Never commit `.env` file to git (use `.gitignore`)
- Always use HTTPS in production
- Enable CAPTCHA for public forms
- Whitelist only trusted domains
- Use environment variables for all secrets
- Regularly rotate Gmail App Password
- Monitor logs for suspicious activity

## Troubleshooting

### "Origin not allowed" Error
- Check `ALLOWED_DOMAINS` in `.env`
- Ensure the domain matches (without protocol or port for some cases)

### "CAPTCHA verification failed"
- Verify Site Key and Secret Key match
- Check that CAPTCHA keys are for the correct domain

### Gmail Authentication Failed
- Verify you're using App Password, not regular Gmail password
- Ensure 2FA is enabled on Google Account
- Check that `GMAIL_USER` and `GMAIL_APP_PASSWORD` are correct

### CORS Errors
- Add your domain to `CORS_ORIGINS` in `.env`
- Format: `https://domain.com,https://www.domain.com`
- Restart the backend after changing `.env`

## Project Structure

```
.
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment variables
└── README.md              # This file
```


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 💖 Support the Project

Love this worker? Here's how you can help:

- 🍴 **Fork it** and add your own features
- 🐛 **Report bugs** or suggest improvements via [GitHub Issues](https://github.com/H190K/Email-Sending-Service/issues)
- 📢 **Share it** with developers who You think might need this
- ⭐ **Star the repo** to show your support

If my projects make your life easier, consider buying me a coffee! Your support helps me create more open-source tools for the community.

<div align="center">

[![Support via DeStream](https://img.shields.io/badge/🍕_Feed_the_Developer-DeStream-FF6B6B?style=for-the-badge)](https://destream.net/live/H190K/donate)

[![Crypto Donations](https://img.shields.io/badge/Crypto_Donations-NOWPayments-9B59B6?style=for-the-badge&logo=bitcoin&logoColor=colored)](https://nowpayments.io/donation?api_key=J0QACAH-BTH4F4F-QDXM4ZS-RCA58BH)

</div>

---

<div align="center">

**Built with ❤️ by [H190K](https://github.com/H190K)**



</div>
