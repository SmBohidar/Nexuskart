# Nexuskart Production Deployment Checklist

Deploying a Django application requires moving from a local development setup to a secure, scalable production environment. Here is a comprehensive checklist of everything you need to do before and during deployment.

---

## 1. Environment Variables (`.env`)
You are using `python-decouple`, which is great. On your production server, you must create a new `.env` file (or set environment variables in your hosting provider's dashboard) with the following values:

*   **`DEBUG=False`** (CRITICAL: Never run with `DEBUG=True` in production, as it exposes your code and passwords if an error occurs).
*   **`SECRET_KEY`**: Generate a new, very long, completely random string. Do not use your local secret key.
*   **`ALLOWED_HOSTS`**: Set this to your live domain (e.g., `ALLOWED_HOSTS=nexuskart.com,www.nexuskart.com`).
*   **`DATABASE_URL`**: Update this to point to your production database.
*   **SMTP Settings**: Ensure your `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, and `EMAIL_HOST_PASSWORD` are set with your production email provider (like SendGrid, Amazon SES, or Gmail App Passwords).

## 2. Database Migration
*   **Switch from SQLite**: You are currently using `db.sqlite3`. SQLite is not designed for production concurrency. You should provision a **PostgreSQL** or **MySQL** database on your production server.
*   **Run Migrations**: After connecting your live database via `DATABASE_URL`, run:
    ```bash
    python manage.py migrate
    ```
*   **Create Superuser**: You will need a new admin account for the live database:
    ```bash
    python manage.py createsuperuser
    ```

## 3. Static and Media Files
*   **Static Files (CSS/JS)**: You are already using `WhiteNoise`, which is perfect for serving static files in production. During deployment, you MUST run:
    ```bash
    python manage.py collectstatic --noinput
    ```
*   **Media Files (User Uploads/Products)**: WhiteNoise **does not** serve user-uploaded media files efficiently or persistently across server restarts (especially on platforms like Heroku/Render). You should configure **Amazon S3** or **Cloudinary** using the `django-storages` package to host your `MEDIA_ROOT`.

## 4. The Sites Framework (Domain Updates)
As we discussed earlier:
1. Log into your production admin panel at `https://yourdomain.com/securelogin/`.
2. Navigate to **Sites** > **Sites**.
3. Change the default `example.com` domain to your actual live domain (e.g., `www.nexuskart.com`).
4. **Why?** This ensures password reset emails and account activation links use your real domain name.

## 5. Security Settings
Add the following to your `settings.py` (or control them via `.env` flags) to force secure connections once your site has an SSL certificate (HTTPS):
```python
# Force all HTTP traffic to HTTPS
SECURE_SSL_REDIRECT = True

# Secure cookies so they are only sent over HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS to tell browsers to only ever use HTTPS
SECURE_HSTS_SECONDS = 31536000 # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

## 6. Social Authentication (Google OAuth)
Since you are using Google Login:
1. Go to your **Google Cloud Console**.
2. Find your OAuth 2.0 Client IDs.
3. Add your production domain to the **Authorized JavaScript origins** (e.g., `https://www.nexuskart.com`).
4. Add your production callback URL to the **Authorized redirect URIs** (e.g., `https://www.nexuskart.com/accounts/google/login/callback/`).
5. *If you forget this, Google Login will throw a "Redirect URI mismatch" error in production.*

## 7. Web Server (Gunicorn & Nginx)
*   **Do not use `python manage.py runserver`** in production. It is single-threaded and insecure.
*   Instead, use a WSGI server like **Gunicorn**:
    ```bash
    pip install gunicorn
    gunicorn nexuskart.wsgi:application --bind 0.0.0.0:8000 --workers 3
    ```
*   Typically, you will place **Nginx** in front of Gunicorn to act as a reverse proxy and handle SSL/HTTPS.

## 8. Inventory & Stock Management
*   **The Integration**: We have deeply integrated inventory control directly into the Django Administration API.
*   **How it works**: By clicking **"Manage"** in the "Low stock items" section of your custom admin dashboard, superadmins are securely redirected to the Django backend. You can update the stock numbers directly from the product list and click save without entering each product individually.
*   **Security Notice**: Ensure that any staff member who needs to update stock is granted `Superuser` status or explicitly given permission to edit the `Product` model via the Django Admin panel. 

## 9. Admin Route Security & Error Pages
*   **404 Obfuscation**: We configured your custom admin dashboard (`/accounts/admin-dashboard/` and related routes) to return a **404 Not Found** or perform a **silent redirect** if a non-staff user tries to access them. This prevents attackers from knowing those URLs even exist.
*   **Custom 404 Page**: Once `DEBUG=False` is set in production, Django will automatically serve the custom `404.html` template we created. Do not be alarmed if you see the yellow Django debug page locally; the beautiful custom 404 page will take over in production.

## 10. Order Cancellation Workflow
*   **Customer Requests**: Customers can explicitly request order cancellations from their `my_orders` dashboard.
*   **Database Tracking**: This relies on the `cancellation_requested` boolean field we added to the `Order` model. Make sure you have run `python manage.py migrate` on your production database so this column exists!
*   **Admin Notifications**: As an admin, you will receive real-time notifications in your dashboard bell and see red highlighted rows in the Recent Orders table. From there, you can process the cancellation with a single click.

## 11. Final Checklist Before Launch
- [ ] Are Stripe / PayPal keys swapped from "Test" to "Live" credentials?
- [ ] Is `DEBUG=False`?
- [ ] Is `html2pdf.js` generating invoices correctly on the live domain?
- [ ] Have you tested the entire checkout flow as a regular user on the live domain?
- [ ] Is your Admin Dashboard (`/securelogin/`) secured with a strong password?
