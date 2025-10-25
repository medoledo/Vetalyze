# Vetalyze Backend - Quick Reference Card

## 🚀 Common Commands

### Development Server
```bash
python manage.py runserver
```

### Background Task (Manual Run)
```bash
python manage.py update_subscription_statuses
```

### Run Tests
```bash
python manage.py test                    # All tests
python manage.py test accounts           # Specific app
python manage.py test --verbosity=2      # Verbose output
```

### Database
```bash
python manage.py makemigrations          # Create migrations
python manage.py migrate                 # Apply migrations
python manage.py createsuperuser         # Create admin user
python manage.py shell                   # Django shell
```

---

## 🔑 Authentication Endpoints

### Login
```bash
POST /api/accounts/token/
Body: {"username": "user", "password": "pass"}
```

### Refresh Token
```bash
POST /api/accounts/token/refresh/
Body: {"refresh": "refresh_token_here"}
```

### Logout
```bash
POST /api/accounts/logout/
Header: Authorization: Bearer <access_token>
Body: {"refresh": "refresh_token_here"}
```

---

## 🏥 Key API Endpoints

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/api/accounts/clinics/` | GET | Site Owner | List all clinics |
| `/api/accounts/clinics/` | POST | Site Owner | Create clinic |
| `/api/accounts/clinics/<id>/` | GET | Site Owner, Owner | Get clinic details |
| `/api/accounts/clinics/me/` | GET | Clinic Owner | Get my profile |
| `/api/accounts/clinics/<id>/subscriptions/` | GET | Site Owner | List subscriptions |
| `/api/accounts/clinics/<id>/subscriptions/` | POST | Site Owner | Create subscription |
| `/api/accounts/doctors/` | GET/POST | Clinic Owner | Manage doctors |
| `/api/accounts/receptionists/` | GET/POST | Clinic Owner | Manage receptionists |
| `/api/owners/` | GET/POST | Clinic Staff | Manage pet owners |

---

## 📋 User Roles

| Role | Permissions |
|------|------------|
| **SITE_OWNER** | Full system access, manage all clinics |
| **CLINIC_OWNER** | Manage own clinic, staff, subscriptions |
| **DOCTOR** | Access clinic data, view patients |
| **RECEPTION** | Front desk operations |

---

## 🔄 Subscription Statuses

| Status | Description |
|--------|-------------|
| **INACTIVE** | Clinic has no subscription |
| **UPCOMING** | Subscription scheduled for future |
| **ACTIVE** | Currently active subscription |
| **SUSPENDED** | Temporarily suspended by admin |
| **ENDED** | Subscription expired naturally |
| **REFUNDED** | Subscription refunded |

---

## ⚠️ Error Codes

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `inactive_user` | 403 | User account deactivated |
| `inactive_clinic` | 403 | Clinic inactive/suspended |
| `subscription_expired` | 402 | Subscription expired |
| `overlapping_subscription` | 400 | Date conflicts |
| `suspended_clinic` | 403 | Clinic suspended |
| `invalid_status_transition` | 400 | Invalid status change |
| `account_limit_exceeded` | 403 | Too many accounts |

---

## 📄 Pagination

### Parameters
- `page=1` - Page number
- `page_size=20` - Items per page (max 100)
- `all=true` - **Site owners only**: Get all results without pagination

### Examples
```bash
# Paginated (default)
GET /api/accounts/clinics/

# Custom page size
GET /api/accounts/clinics/?page_size=50

# All results (site owners only)
GET /api/accounts/clinics/?all=true
```

### Response Format
```json
{
  "count": 150,
  "next": "/api/resource/?page=2",
  "previous": null,
  "results": [...]
}
```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `settings.py` | Configuration |
| `db.sqlite3` | Database (dev) |
| `logs/app.log` | Application logs |
| `private.pem` | JWT signing key |
| `public.pem` | JWT verification key |

---

## 🔧 Troubleshooting

### Port in use
```bash
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Database issues
```bash
python manage.py migrate
```

### Clear logs
```bash
del logs\app.log           # Windows
rm logs/app.log            # Linux
```

### Reset database (DEV ONLY!)
```bash
del db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

---

## 📊 Monitoring

### Check Logs
```bash
# Windows
type logs\app.log
type logs\subscription_update.log

# Linux
cat logs/app.log
tail -f logs/app.log        # Follow logs
```

### View Recent Errors
```bash
# Windows
findstr "ERROR" logs\app.log

# Linux
grep "ERROR" logs/app.log
```

---

## 🔐 Security Checklist

Production deployment:
- [ ] Set `DEBUG = False`
- [ ] Change `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Setup HTTPS
- [ ] Secure `private.pem` permissions
- [ ] Use PostgreSQL (not SQLite)
- [ ] Setup firewall
- [ ] Enable security headers
- [ ] Regular backups
- [ ] Monitor logs

---

## 📞 Getting Help

1. Check error message and code
2. Review logs: `logs/app.log`
3. Check documentation:
   - `README.md` - Main guide
   - `API_DOCUMENTATION.md` - API reference
   - `SETUP_GUIDE.md` - Setup instructions
4. Run tests: `python manage.py test`
5. Contact development team

---

## 🎯 Daily Operations

### Morning Checklist
- [ ] Check logs for errors
- [ ] Verify background task ran
- [ ] Check disk space
- [ ] Review new subscriptions

### Weekly Checklist
- [ ] Backup database
- [ ] Review subscription statuses
- [ ] Check system performance
- [ ] Update dependencies if needed

### Monthly Checklist
- [ ] Security audit
- [ ] Performance review
- [ ] Log rotation check
- [ ] Documentation updates

---

**Quick Links**:
- API Docs: `API_DOCUMENTATION.md`
- Setup Guide: `SETUP_GUIDE.md`
- Full README: `README.md`
- Changes: `CHANGELOG.md`
