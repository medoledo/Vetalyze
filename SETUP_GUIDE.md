# Vetalyze Backend - Quick Setup Guide

## Initial Setup

### 1. Install Dependencies

```bash
cd c:\Users\medol\OneDrive\Desktop\vetalyze\backend
pip install -r requirements.txt
```

### 2. Create Logs Directory

```bash
mkdir logs
```

### 3. Run Database Migrations

```bash
python manage.py migrate
```

### 4. Create Superuser (Site Owner)

```bash
python manage.py createsuperuser
```

Follow the prompts:
- Username: `admin` (or your choice)
- Email: (optional)
- Password: (enter secure password)

After creation, you need to set the role to SITE_OWNER in Django admin or database.

### 5. Create Initial Data

#### Option A: Using Django Shell

```bash
python manage.py shell
```

Then run:

```python
from accounts.models import User, Country, SubscriptionType, PaymentMethod

# Update superuser role to SITE_OWNER
admin = User.objects.get(username='admin')
admin.role = User.Role.SITE_OWNER
admin.save()

# Create a country
country = Country.objects.create(
    name='Egypt',
    max_id_number=14,
    max_phone_number=11
)

# Create subscription types
monthly = SubscriptionType.objects.create(
    name='Monthly Plan',
    price=100.00,
    duration_days=30,
    allowed_accounts=5
)

quarterly = SubscriptionType.objects.create(
    name='Quarterly Plan',
    price=270.00,
    duration_days=90,
    allowed_accounts=10
)

annual = SubscriptionType.objects.create(
    name='Annual Plan',
    price=1000.00,
    duration_days=365,
    allowed_accounts=20
)

# Create payment methods
PaymentMethod.objects.create(name='Cash')
PaymentMethod.objects.create(name='Bank Transfer')
PaymentMethod.objects.create(name='Credit Card')

# Create marketing channels
from owners.models import MarketingChannel, PetType

MarketingChannel.objects.create(name='Facebook')
MarketingChannel.objects.create(name='Instagram')
MarketingChannel.objects.create(name='Google')
MarketingChannel.objects.create(name='Friend Referral')

# Create pet types
PetType.objects.create(name='Dog')
PetType.objects.create(name='Cat')
PetType.objects.create(name='Bird')
PetType.objects.create(name='Rabbit')

exit()
```

#### Option B: Using Django Admin

1. Run the server: `python manage.py runserver`
2. Go to: `http://127.0.0.1:8000/admin/`
3. Login with superuser credentials
4. Add Country, SubscriptionType, PaymentMethod, etc.

### 6. Test the Setup

```bash
# Run tests
python manage.py test

# Test the subscription update command
python manage.py update_subscription_statuses
```

### 7. Start the Development Server

```bash
python manage.py runserver
```

Access the API at: `http://127.0.0.1:8000/api/`

---

## Setting Up Background Task (Windows)

### Create Task in Windows Task Scheduler

1. Open **Task Scheduler** (search in Start menu)

2. Click **"Create Basic Task"**

3. Enter Task Details:
   - Name: `Vetalyze Subscription Update`
   - Description: `Daily task to update subscription statuses`

4. Set Trigger:
   - When: **Daily**
   - Start: Choose today's date
   - Time: **12:01 AM**
   - Recur every: **1 days**

5. Set Action:
   - Action: **Start a program**
   - Program/script: Browse to `c:\Users\medol\OneDrive\Desktop\vetalyze\backend\update_subscriptions.bat`
   - Start in: `c:\Users\medol\OneDrive\Desktop\vetalyze\backend`

6. Review and click **Finish**

7. Right-click the task and select **Properties**:
   - General tab:
     - Select "Run whether user is logged on or not"
     - Check "Run with highest privileges"
   - Settings tab:
     - Check "Run task as soon as possible after a scheduled start is missed"

8. Click **OK** and enter your Windows password if prompted

### Verify Task is Working

Check the log file after the task runs:
```bash
type logs\subscription_update.log
```

Or manually run the task:
1. Open Task Scheduler
2. Find your task
3. Right-click and select **Run**
4. Check the logs

---

## Testing the API

### 1. Get Access Token (Login)

```bash
curl -X POST http://127.0.0.1:8000/api/accounts/token/ ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"admin\", \"password\": \"your_password\"}"
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "role": "SITE_OWNER",
  "clinic_name": "Vetalyze"
}
```

### 2. Create a Clinic Owner

```bash
curl -X POST http://127.0.0.1:8000/api/accounts/clinics/ ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"user\": {\"username\": \"clinic1\", \"password\": \"pass123\"}, \"country_id\": 1, \"clinic_owner_name\": \"Dr. Ahmed\", \"clinic_name\": \"Test Clinic\", \"owner_phone_number\": \"01234567890\", \"clinic_phone_number\": \"01234567890\"}"
```

### 3. Create a Subscription

```bash
curl -X POST http://127.0.0.1:8000/api/accounts/clinics/CLINIC_ID/subscriptions/ ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"subscription_type_id\": 1, \"payment_method_id\": 1, \"amount_paid\": \"100.00\", \"start_date\": \"2024-10-24\"}"
```

### 4. Login as Clinic Owner

```bash
curl -X POST http://127.0.0.1:8000/api/accounts/token/ ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"clinic1\", \"password\": \"pass123\"}"
```

---

## Common Commands

### Database Management

```bash
# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Reset database (SQLite only - careful!)
del db.sqlite3
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test accounts

# Run with verbose output
python manage.py test --verbosity=2

# Run specific test class
python manage.py test accounts.tests.AuthenticationAPITest
```

### Management Commands

```bash
# Update subscription statuses
python manage.py update_subscription_statuses

# Create shell session
python manage.py shell

# Collect static files
python manage.py collectstatic
```

### Server

```bash
# Development server
python manage.py runserver

# Run on specific port
python manage.py runserver 8080

# Run on all interfaces
python manage.py runserver 0.0.0.0:8000
```

---

## Troubleshooting

### Issue: "No such table" error

**Solution**:
```bash
python manage.py migrate
```

### Issue: Port already in use

**Solution**:
```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID <PID> /F

# Or use a different port
python manage.py runserver 8080
```

### Issue: Background task not running

**Solution**:
1. Check Task Scheduler for errors
2. Verify batch file path is correct
3. Check logs in `logs\subscription_update.log`
4. Run batch file manually to test

### Issue: JWT token errors

**Solution**:
- Ensure `private.pem` and `public.pem` exist
- Check file permissions
- Verify token format in Authorization header

### Issue: CORS errors from frontend

**Solution**:
Update `CORS_ALLOWED_ORIGINS` in `settings.py`:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

---

## Next Steps

1. **Create test data** using Django admin or API
2. **Test all API endpoints** using Postman or curl
3. **Setup the frontend** to connect to this backend
4. **Configure production settings** when deploying
5. **Setup monitoring** for logs and errors
6. **Regular backups** of the database

---

## Production Deployment

See [README.md](README.md) for complete production deployment checklist.

Key points:
- Set `DEBUG = False`
- Use PostgreSQL instead of SQLite
- Configure environment variables
- Setup HTTPS
- Enable security settings
- Configure cron job (Linux) or Task Scheduler (Windows)
- Setup log monitoring
- Regular database backups

---

## Support

- See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for API reference
- See [README.md](README.md) for detailed documentation
- Contact development team for support

---

**Setup Complete!** Your Vetalyze backend is ready to use.
