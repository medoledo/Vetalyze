# Vetalyze Backend - Veterinary Clinic Management System

## Overview

Vetalyze is a comprehensive backend system for managing veterinary clinics, designed to handle multiple clinics with subscription-based access control. The system provides robust user management, subscription handling, and clinic operations management.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Background Tasks](#background-tasks)
- [Testing](#testing)
- [Security](#security)
- [Deployment](#deployment)

## Features

### User Management
- **Multi-role authentication system**: Admin, Site Owner, Clinic Owner, Doctor, Reception
- **JWT-based authentication** with RSA signing
- **Token refresh and blacklisting** for secure logout
- **Role-based access control** with custom permissions

### Subscription Management
- **Flexible subscription plans** with configurable duration and pricing
- **Automated subscription lifecycle management**
  - Automatic activation of upcoming subscriptions
  - Automatic expiration of ended subscriptions
  - Background task runs daily at 12:01 AM
- **Subscription status tracking**: UPCOMING, ACTIVE, ENDED, SUSPENDED, REFUNDED
- **Clinic status synchronization** with subscription state
- **Overlapping subscription prevention**

### Clinic Operations
- **Clinic owner profile management**
- **Doctor and receptionist account management**
- **Pet owner (client) management**
- **Pet records management**
- **Country-specific validation rules** (phone numbers, ID numbers)

### Data Integrity & Performance
- **Atomic transactions** for critical operations
- **Database query optimization** with select_related and prefetch_related
- **Comprehensive error handling and logging**
- **Custom exception classes** for clear error messages
- **Validation at multiple levels** (model, serializer, view)

## Architecture

### Tech Stack
- **Framework**: Django 5.2.6
- **API**: Django REST Framework
- **Authentication**: SimpleJWT with RS256 (RSA keys)
- **Database**: SQLite (development), PostgreSQL recommended for production
- **CORS**: django-cors-headers

### Project Structure
```
backend/
├── accounts/               # User management and authentication
│   ├── management/
│   │   └── commands/
│   │       └── update_subscription_statuses.py
│   ├── exceptions.py      # Custom exception classes
│   ├── models.py          # User, Profile, Subscription models
│   ├── serializers.py     # API serializers
│   ├── views.py           # API views
│   ├── permissions.py     # Custom permissions
│   ├── urls.py            # URL routing
│   └── tests.py           # Unit tests
├── owners/                # Pet owner and pet management
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── backend/               # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── logs/                  # Application logs
├── static/                # Static files
├── media/                 # Media files
├── update_subscriptions.bat  # Windows Task Scheduler script
└── manage.py
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Steps

1. **Clone the repository** (or navigate to the project directory)
   ```bash
   cd c:\Users\medol\OneDrive\Desktop\vetalyze\backend
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create logs directory**
   ```bash
   mkdir logs
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files** (for production)
   ```bash
   python manage.py collectstatic
   ```

## Configuration

### Environment Variables (Recommended for Production)

Create a `.env` file in the backend directory:

```env
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost/dbname
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

### JWT Keys

The application uses RSA keys for JWT signing. The keys are located at:
- `private.pem` - Private key for signing tokens
- `public.pem` - Public key for verification

**Important**: In production, ensure these keys are:
- Kept secure and not committed to version control
- Have appropriate file permissions (read-only)
- Backed up securely

### Database Configuration

For production, update `settings.py` to use PostgreSQL:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'vetalyze_db',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Running the Application

### Development Server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`

### Production Server

Use a production-grade WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn backend.wsgi:application --bind 0.0.0.0:8000
```

Or use uWSGI, Waitress, or your preferred WSGI server.

## Background Tasks

### Subscription Status Update Task

The system includes a management command that automatically updates subscription statuses. This task should run daily at 12:01 AM.

#### What it does:
1. **Activates upcoming subscriptions** whose start date has arrived
2. **Expires active subscriptions** whose end date has passed
3. **Updates clinic statuses** based on subscription state
4. **Logs all operations** for audit trail

#### Manual Execution

```bash
python manage.py update_subscription_statuses
```

#### Windows Task Scheduler Setup

1. Open **Task Scheduler**
2. Click **Create Basic Task**
3. Name: "Vetalyze Subscription Update"
4. Trigger: **Daily** at **12:01 AM**
5. Action: **Start a program**
6. Program/script: Browse to `update_subscriptions.bat`
7. Start in: `c:\Users\medol\OneDrive\Desktop\vetalyze\backend`
8. Click **Finish**

#### Linux/Unix Cron Setup

Add to crontab:
```bash
1 0 * * * cd /path/to/vetalyze/backend && /path/to/python manage.py update_subscription_statuses >> logs/subscription_update.log 2>&1
```

## Testing

### Running All Tests

```bash
python manage.py test
```

### Running Specific Test Classes

```bash
python manage.py test accounts.tests.UserModelTest
python manage.py test accounts.tests.AuthenticationAPITest
python manage.py test accounts.tests.SubscriptionManagementTest
```

### Test Coverage

The test suite includes:
- **Model tests**: User, ClinicOwnerProfile, SubscriptionHistory
- **API tests**: Authentication, subscription management
- **Integration tests**: Login, token refresh, subscription creation
- **Management command tests**: Subscription status updates

## Security

### Authentication & Authorization
- JWT tokens with RS256 algorithm (RSA signing)
- Refresh token rotation and blacklisting
- Role-based access control (RBAC)
- User and clinic status validation on every request

### Data Protection
- Atomic database transactions for critical operations
- Input validation at multiple levels
- SQL injection prevention (Django ORM)
- XSS protection (Django templates)

### Production Security Checklist
- [ ] Set `DEBUG = False`
- [ ] Use strong `SECRET_KEY`
- [ ] Enable HTTPS (`SECURE_SSL_REDIRECT = True`)
- [ ] Set secure cookie flags
- [ ] Configure ALLOWED_HOSTS properly
- [ ] Use environment variables for sensitive data
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity

## Logging

Logs are stored in the `logs/` directory:
- `app.log` - Application logs (rotates at 10MB, keeps 5 backups)
- `subscription_update.log` - Background task execution logs

### Log Levels
- **INFO**: Normal operations, successful actions
- **WARNING**: Potential issues, unauthorized access attempts
- **ERROR**: Failed operations, exceptions

## API Endpoints

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete API reference.

## Error Handling

The system uses custom exception classes for consistent error responses:

- `InactiveUserError` (403): User account is deactivated
- `InactiveClinicError` (403): Clinic is inactive/suspended
- `SubscriptionExpiredError` (402): Subscription has expired
- `OverlappingSubscriptionError` (400): Subscription dates overlap
- `SuspendedClinicError` (403): Clinic is suspended
- `InvalidSubscriptionStatusError` (400): Invalid status transition
- `AccountLimitExceededError` (403): Subscription account limit reached

## Troubleshooting

### Common Issues

**Issue**: Subscription not activating automatically
- **Solution**: Check if the background task is running. Verify Windows Task Scheduler or cron job configuration.

**Issue**: JWT token errors
- **Solution**: Ensure `private.pem` and `public.pem` exist and have correct permissions.

**Issue**: Database locked errors (SQLite)
- **Solution**: SQLite is not recommended for production. Migrate to PostgreSQL.

**Issue**: CORS errors
- **Solution**: Verify `CORS_ALLOWED_ORIGINS` in settings.py matches your frontend URL.

## Deployment

### Production Checklist

1. **Environment Setup**
   - [ ] Set environment variables
   - [ ] Configure production database
   - [ ] Set DEBUG=False
   - [ ] Configure ALLOWED_HOSTS

2. **Static Files**
   - [ ] Run `collectstatic`
   - [ ] Configure web server to serve static files

3. **Database**
   - [ ] Run migrations
   - [ ] Create superuser
   - [ ] Backup database regularly

4. **Background Tasks**
   - [ ] Setup cron job or task scheduler
   - [ ] Test subscription update command

5. **Monitoring**
   - [ ] Setup log monitoring
   - [ ] Configure error notifications
   - [ ] Monitor disk space (logs)

6. **Security**
   - [ ] Complete security checklist
   - [ ] Regular security audits
   - [ ] Keep dependencies updated

## Contributing

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to classes and methods
- Write tests for new features

### Commit Guidelines
- Use clear, descriptive commit messages
- Reference issue numbers where applicable
- Keep commits focused and atomic

## License

[Add your license information here]

## Support

For issues, questions, or contributions:
- Create an issue in the repository
- Contact the development team
- Check the API documentation

## Version History

### Version 1.0.0 (Current)
- Initial release
- User management system
- Subscription management
- Background task for subscription updates
- Comprehensive error handling
- Unit test coverage
- API documentation
