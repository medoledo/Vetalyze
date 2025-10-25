# Vetalyze API Documentation

## Base URL
```
Development: http://127.0.0.1:8000/api/
Production: https://yourdomain.com/api/
```

## Authentication

The API uses JWT (JSON Web Token) authentication with RS256 algorithm.

### Headers
All authenticated requests must include:
```
Authorization: Bearer <access_token>
```

### Token Lifecycle
- **Access Token**: Valid for 30 minutes
- **Refresh Token**: Valid for 7 days
- **Token Rotation**: New refresh token issued on each refresh

---

## Table of Contents

1. [Authentication Endpoints](#authentication-endpoints)
2. [Clinic Owner Management](#clinic-owner-management)
3. [Subscription Management](#subscription-management)
4. [Doctor Management](#doctor-management)
5. [Reception Management](#reception-management)
6. [Pet Owner Management](#pet-owner-management)
7. [Reference Data](#reference-data)
8. [Pagination](#pagination)
9. [Error Codes](#error-codes)

---

## Pagination

Most list endpoints support pagination to improve performance and reduce response times. The API uses page-based pagination with the following defaults:

### Pagination Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number to retrieve |
| `page_size` | integer | 20 | Number of items per page (max: 100) |
| `all` | boolean | false | **Site owners only**: Bypass pagination to get all results |

### Paginated Response Format

```json
{
  "count": 150,           // Total number of items
  "next": "http://api.example.com/resource/?page=2&page_size=20",
  "previous": null,
  "results": [...]        // Array of items
}
```

### Bypassing Pagination (Site Owners Only)

Site owners can retrieve all results without pagination by adding `all=true` to the query parameters:

```
GET /api/accounts/clinics/?all=true
```

**Requirements:**
- Must be authenticated as a Site Owner
- Returns all results in a single response
- No pagination metadata included

**Error Response (403 Forbidden):**
```json
{
  "error": "Pagination bypass not allowed. You must be a site owner to retrieve all data without pagination.",
  "code": "pagination_bypass_not_allowed"
}
```

### Page Size Limits

- **Default**: 20 items per page
- **Maximum**: 100 items per page
- **Minimum**: 1 item per page

### Example Requests

```bash
# Get first page (default)
GET /api/accounts/clinics/

# Get specific page with custom size
GET /api/accounts/clinics/?page=2&page_size=50

# Get all results (site owners only)
GET /api/accounts/clinics/?all=true
```

---

## Authentication Endpoints

### 1. Login (Obtain Token Pair)

Authenticate a user and receive access and refresh tokens.

**Endpoint**: `POST /api/accounts/token/`

**Permissions**: Public

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Success Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "role": "CLINIC_OWNER",
  "clinic_name": "Test Clinic"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid credentials
- `403 Forbidden`: User account inactive or clinic inactive

**Example**:
```bash
curl -X POST http://127.0.0.1:8000/api/accounts/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "clinicowner", "password": "pass123"}'
```

---

### 2. Refresh Token

Get a new access token using a refresh token.

**Endpoint**: `POST /api/accounts/token/refresh/`

**Permissions**: Public

**Request Body**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Success Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "role": "CLINIC_OWNER",
  "clinic_name": "Test Clinic"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or expired refresh token
- `403 Forbidden`: User account inactive or clinic inactive

---

### 3. Logout

Blacklist a refresh token to log out.

**Endpoint**: `POST /api/accounts/logout/`

**Permissions**: Authenticated users

**Headers**: 
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Success Response** (205 Reset Content):
```json
{
  "message": "Successfully logged out."
}
```

**Error Responses**:
- `400 Bad Request`: Refresh token missing or invalid
- `401 Unauthorized`: Not authenticated

---

### 4. Get Public Key

Retrieve the RSA public key for JWT verification (for external services).

**Endpoint**: `GET /api/accounts/public-key/`

**Permissions**: Public

**Success Response** (200 OK):
```json
{
  "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBg..."
}
```

---

## Clinic Owner Management

### 5. List All Clinic Owners

Get a list of all clinic owner profiles.

**Endpoint**: `GET /api/accounts/clinics/`

**Permissions**: Site Owner only

**Query Parameters**:
- None (returns all clinics)

**Success Response** (200 OK):
```json
[
  {
    "user": {
      "id": 1,
      "username": "clinic1",
      "role": "CLINIC_OWNER"
    },
    "country": {
      "id": 1,
      "name": "Egypt",
      "max_id_number": 14,
      "max_phone_number": 11
    },
    "clinic_owner_name": "Dr. Ahmed Hassan",
    "clinic_name": "Cairo Veterinary Clinic",
    "owner_phone_number": "01234567890",
    "clinic_phone_number": "01234567890",
    "location": "Cairo, Egypt",
    "status": "ACTIVE",
    "joined_date": "2024-01-15",
    "current_plan": {
      "id": 1,
      "name": "Monthly Plan",
      "price": "100.00",
      "duration_days": 30,
      "allowed_accounts": 5
    },
    "days_left": 15,
    "added_by": "siteowner"
  }
]
```

---

### 6. Create Clinic Owner

Create a new clinic owner profile.

**Endpoint**: `POST /api/accounts/clinics/`

**Permissions**: Site Owner only

**Request Body**:
```json
{
  "user": {
    "username": "newclinic",
    "password": "securepass123"
  },
  "country_id": 1,
  "clinic_owner_name": "Dr. Sara Ali",
  "clinic_name": "Alexandria Pet Clinic",
  "owner_phone_number": "01098765432",
  "clinic_phone_number": "01098765432",
  "location": "Alexandria, Egypt",
  "facebook": "https://facebook.com/alexpetclinic",
  "website": "https://alexpetclinic.com",
  "gmail": "info@alexpetclinic.com"
}
```

**Success Response** (201 Created):
```json
{
  "user": {
    "id": 5,
    "username": "newclinic",
    "role": "CLINIC_OWNER"
  },
  "country": {...},
  "clinic_owner_name": "Dr. Sara Ali",
  "clinic_name": "Alexandria Pet Clinic",
  "status": "INACTIVE",
  "joined_date": "2024-10-24"
}
```

**Validation Rules**:
- Username must be unique
- Phone numbers must match country's max length
- All required fields must be provided

**Error Responses**:
- `400 Bad Request`: Validation error
- `403 Forbidden`: Not a site owner

---

### 7. Get Clinic Owner Details

Retrieve details of a specific clinic owner.

**Endpoint**: `GET /api/accounts/clinics/<clinic_id>/`

**Permissions**: 
- Site Owner: Can view any clinic
- Clinic Owner: Can view only their own profile

**Success Response** (200 OK):
```json
{
  "user": {...},
  "country": {...},
  "clinic_owner_name": "Dr. Ahmed Hassan",
  "clinic_name": "Cairo Veterinary Clinic",
  "status": "ACTIVE",
  "current_plan": {...},
  "subscription_history": [
    {
      "id": 1,
      "subscription_type": {...},
      "payment_method": {...},
      "start_date": "2024-01-15",
      "end_date": "2024-02-14",
      "status": "ACTIVE",
      "amount_paid": "100.00",
      "days_left": 15
    }
  ]
}
```

---

### 8. Update Clinic Owner

Update clinic owner profile information.

**Endpoint**: `PATCH /api/accounts/clinics/<clinic_id>/`

**Permissions**: Site Owner only

**Request Body** (partial update):
```json
{
  "clinic_name": "Updated Clinic Name",
  "location": "New Location",
  "website": "https://newwebsite.com"
}
```

**Success Response** (200 OK):
```json
{
  "user": {...},
  "clinic_name": "Updated Clinic Name",
  "location": "New Location",
  ...
}
```

**Note**: Cannot update user credentials through this endpoint.

---

### 9. Get My Profile (Clinic Owner)

Clinic owner can retrieve their own profile.

**Endpoint**: `GET /api/accounts/clinics/me/`

**Permissions**: Clinic Owner only

**Success Response** (200 OK):
```json
{
  "user": {...},
  "clinic_name": "Cairo Veterinary Clinic",
  "status": "ACTIVE",
  "current_plan": {...},
  "subscription_history": [...]
}
```

---

### 10. Change Password

Change password for a clinic owner.

**Endpoint**: `POST /api/accounts/clinics/<clinic_id>/change-password/`

**Permissions**:
- Site Owner: Can change any clinic owner's password
- Clinic Owner: Can change only their own password

**Request Body**:
```json
{
  "current_password": "oldpass123",  // Required for clinic owners
  "new_password": "newpass456",
  "confirm_new_password": "newpass456"
}
```

**Success Response** (200 OK):
```json
{
  "message": "Password changed successfully."
}
```

**Validation Rules**:
- New passwords must match
- Clinic owners must provide correct current password
- Site owners don't need current password

**Error Responses**:
- `400 Bad Request`: Validation error, passwords don't match
- `403 Forbidden`: Unauthorized to change this password

---

## Subscription Management

### 11. List Subscription History

Get subscription history for a specific clinic.

**Endpoint**: `GET /api/accounts/clinics/<clinic_id>/subscriptions/`

**Permissions**: Site Owner only

**Success Response** (200 OK):
```json
[
  {
    "id": 1,
    "subscription_group": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "subscription_type": {
      "id": 1,
      "name": "Monthly Plan",
      "price": "100.00",
      "duration_days": 30,
      "allowed_accounts": 5
    },
    "payment_method": {
      "id": 1,
      "name": "Cash"
    },
    "activated_by": {
      "id": 1,
      "username": "siteowner",
      "role": "SITE_OWNER"
    },
    "extra_accounts_number": 2,
    "ref_number": "REF12345",
    "amount_paid": "120.00",
    "comments": "Initial subscription",
    "activation_date": "2024-01-15",
    "start_date": "2024-01-15",
    "end_date": "2024-02-14",
    "status": "ACTIVE",
    "days_left": 15,
    "clinic": 1
  }
]
```

---

### 12. Create Subscription

Create a new subscription for a clinic.

**Endpoint**: `POST /api/accounts/clinics/<clinic_id>/subscriptions/`

**Permissions**: Site Owner only

**Request Body**:
```json
{
  "subscription_type_id": 1,
  "payment_method_id": 1,
  "amount_paid": "100.00",
  "start_date": "2024-10-24",
  "extra_accounts_number": 2,
  "ref_number": "REF67890",
  "comments": "New subscription for Q4"
}
```

**Success Response** (201 Created):
```json
{
  "id": 5,
  "subscription_type": {...},
  "payment_method": {...},
  "start_date": "2024-10-24",
  "end_date": "2024-11-23",  // Auto-calculated
  "status": "ACTIVE",        // Auto-set based on start_date
  "amount_paid": "100.00",
  ...
}
```

**Validation Rules**:
- Cannot create subscription for suspended clinic
- Cannot create overlapping subscriptions
- Start date cannot be in the past
- Amount paid cannot be negative

**Side Effects**:
- If start_date is today: Clinic status becomes ACTIVE
- Any currently active subscription is ended
- Upcoming subscriptions can be queued

**Error Responses**:
- `400 Bad Request`: Overlapping subscription, invalid data
- `403 Forbidden`: Clinic is suspended

---

### 13. Suspend Subscription

Suspend an active subscription.

**Endpoint**: `POST /api/accounts/clinics/<clinic_id>/subscriptions/<sub_id>/manage/`

**Permissions**: Site Owner only

**Request Body**:
```json
{
  "action": "suspend",
  "comment": "Payment issues - suspended until resolved"
}
```

**Success Response** (200 OK):
```json
{
  "message": "Subscription and clinic suspended successfully."
}
```

**Rules**:
- Only ACTIVE subscriptions can be suspended
- Cannot suspend if clinic has upcoming subscriptions
- Creates a new SUSPENDED subscription record
- Ends the current ACTIVE subscription
- Sets clinic status to SUSPENDED

**Error Responses**:
- `400 Bad Request`: Invalid status for suspension
- `404 Not Found`: Subscription not found

---

### 14. Reactivate Subscription

Reactivate a suspended subscription.

**Endpoint**: `POST /api/accounts/clinics/<clinic_id>/subscriptions/<sub_id>/manage/`

**Permissions**: Site Owner only

**Request Body**:
```json
{
  "action": "reactivate",
  "comment": "Payment received - reactivating subscription"
}
```

**Success Response** (200 OK):
```json
{
  "message": "Subscription and clinic reactivated successfully."
}
```

**Rules**:
- Only SUSPENDED subscriptions can be reactivated
- Creates a new ACTIVE subscription record
- Ends the current SUSPENDED subscription
- Sets clinic status to ACTIVE

---

### 15. Refund Subscription

Refund a subscription and optionally end clinic access.

**Endpoint**: `POST /api/accounts/clinics/<clinic_id>/subscriptions/<sub_id>/refund/`

**Permissions**: Site Owner only

**Request Body**:
```json
{
  "comment": "Refund requested by client - service not satisfactory"
}
```

**Success Response** (200 OK):
```json
{
  "message": "Subscription has been refunded successfully."
}
```

**Rules**:
- Can refund: ACTIVE, SUSPENDED, or UPCOMING subscriptions
- Cannot refund: ENDED or REFUNDED subscriptions
- Sets subscription status to REFUNDED
- If no other active/upcoming subscriptions exist, clinic status becomes ENDED

**Error Responses**:
- `400 Bad Request`: Cannot refund subscription in current status
- `404 Not Found`: Subscription not found

---

## Doctor Management

### 16. List Doctors

Get all doctors for the authenticated clinic owner.

**Endpoint**: `GET /api/accounts/doctors/`

**Permissions**: Clinic Owner only

**Success Response** (200 OK):
```json
[
  {
    "user": {
      "id": 10,
      "username": "dr_ahmed",
      "role": "DOCTOR"
    },
    "clinic_owner_profile": 1,
    "full_name": "Dr. Ahmed Mohamed",
    "phone_number": "01112345678",
    "joined_date": "2024-05-10",
    "is_active": true
  }
]
```

---

### 17. Create Doctor

Create a new doctor account for the clinic.

**Endpoint**: `POST /api/accounts/doctors/`

**Permissions**: Clinic Owner only

**Request Body**:
```json
{
  "username": "dr_sara",
  "password": "docpass123",
  "full_name": "Dr. Sara Ali",
  "phone_number": "01123456789"
}
```

**Success Response** (201 Created):
```json
{
  "user": {
    "id": 15,
    "username": "dr_sara",
    "role": "DOCTOR"
  },
  "clinic_owner_profile": 1,
  "full_name": "Dr. Sara Ali",
  "phone_number": "01123456789",
  "joined_date": "2024-10-24",
  "is_active": true
}
```

**Validation Rules**:
- Username must be unique
- Phone number must match country's max length
- Clinic must have available account slots in subscription

---

### 18. Get Doctor Details

Retrieve details of a specific doctor.

**Endpoint**: `GET /api/accounts/doctors/<doctor_id>/`

**Permissions**:
- Clinic Owner: Can view their clinic's doctors
- Doctor: Can view only their own profile

**Success Response** (200 OK):
```json
{
  "user": {...},
  "clinic_owner_profile": 1,
  "full_name": "Dr. Ahmed Mohamed",
  "phone_number": "01112345678",
  "joined_date": "2024-05-10",
  "is_active": true
}
```

---

### 19. Update Doctor

Update doctor information.

**Endpoint**: `PATCH /api/accounts/doctors/<doctor_id>/`

**Permissions**: Clinic Owner only

**Request Body**:
```json
{
  "full_name": "Dr. Ahmed Mohamed Hassan",
  "phone_number": "01198765432",
  "is_active": false
}
```

**Success Response** (200 OK):
```json
{
  "user": {...},
  "full_name": "Dr. Ahmed Mohamed Hassan",
  "phone_number": "01198765432",
  "is_active": false,
  ...
}
```

---

### 20. Delete Doctor

Delete a doctor account.

**Endpoint**: `DELETE /api/accounts/doctors/<doctor_id>/`

**Permissions**: Clinic Owner only

**Success Response** (204 No Content):
- No response body

---

### 21. Get My Profile (Doctor)

Doctor can retrieve their own profile.

**Endpoint**: `GET /api/accounts/doctors/me/`

**Permissions**: Doctor only

**Success Response** (200 OK):
```json
{
  "user": {...},
  "clinic_owner_profile": 1,
  "full_name": "Dr. Ahmed Mohamed",
  "phone_number": "01112345678",
  "is_active": true
}
```

---

## Reception Management

### 22. List Receptionists

Get all receptionists for the authenticated clinic owner.

**Endpoint**: `GET /api/accounts/receptionists/`

**Permissions**: Clinic Owner only

**Success Response** (200 OK):
```json
[
  {
    "user": {
      "id": 20,
      "username": "reception1",
      "role": "RECEPTION"
    },
    "clinic_owner_profile": 1,
    "full_name": "Fatima Hassan",
    "phone_number": "01156789012",
    "joined_date": "2024-03-15",
    "is_active": true
  }
]
```

---

### 23. Create Receptionist

Create a new receptionist account.

**Endpoint**: `POST /api/accounts/receptionists/`

**Permissions**: Clinic Owner only

**Request Body**:
```json
{
  "username": "reception2",
  "password": "recpass123",
  "full_name": "Nora Ahmed",
  "phone_number": "01145678901"
}
```

**Success Response** (201 Created):
```json
{
  "user": {
    "id": 25,
    "username": "reception2",
    "role": "RECEPTION"
  },
  "clinic_owner_profile": 1,
  "full_name": "Nora Ahmed",
  "phone_number": "01145678901",
  "joined_date": "2024-10-24",
  "is_active": true
}
```

---

### 24-27. Reception Management

Similar endpoints to Doctor Management (Get Details, Update, Delete, Get My Profile) with `/api/accounts/receptionists/` base URL.

---

## Pet Owner Management

### 28. List Pet Owners

Get all pet owners (clients) for the clinic.

**Endpoint**: `GET /api/owners/`

**Permissions**: Clinic Owner, Doctor, Reception

**Success Response** (200 OK):
```json
[
  {
    "id": 1,
    "clinic": 1,
    "full_name": "Mohamed Ibrahim",
    "phone_number": "01234567890",
    "second_phone_number": "01098765432",
    "code": "AB12CD3",
    "knew_us_from": {
      "id": 1,
      "name": "Facebook"
    },
    "pets": [
      {
        "id": 1,
        "owner": 1,
        "name": "Max",
        "code": "PET1234",
        "birthday": "2020-05-15",
        "type": {
          "id": 1,
          "name": "Dog"
        }
      }
    ]
  }
]
```

---

### 29. Create Pet Owner

Create a new pet owner (client).

**Endpoint**: `POST /api/owners/`

**Permissions**: Clinic Owner only

**Request Body**:
```json
{
  "full_name": "Sara Ali",
  "phone_number": "01123456789",
  "second_phone_number": "01098765432",
  "knew_us_from": 2,
  "pets": [
    {
      "name": "Whiskers",
      "type": 2,
      "birthday": "2019-08-20"
    }
  ]
}
```

**Success Response** (201 Created):
```json
{
  "id": 5,
  "code": "XY56ZW9",  // Auto-generated
  "full_name": "Sara Ali",
  "phone_number": "01123456789",
  "pets": [
    {
      "id": 10,
      "code": "PET5678",  // Auto-generated
      "name": "Whiskers",
      "type": {...}
    }
  ]
}
```

---

### 30-32. Pet Owner Management

- `GET /api/owners/<owner_id>/` - Get owner details
- `PATCH /api/owners/<owner_id>/` - Update owner
- `DELETE /api/owners/<owner_id>/` - Delete owner

---

## Reference Data

### 33. List Subscription Types

Get all available subscription plans.

**Endpoint**: `GET /api/accounts/subscription-types/`

**Permissions**: Site Owner only

**Success Response** (200 OK):
```json
[
  {
    "id": 1,
    "name": "Monthly Plan",
    "price": "100.00",
    "duration_days": 30,
    "allowed_accounts": 5
  },
  {
    "id": 2,
    "name": "Quarterly Plan",
    "price": "270.00",
    "duration_days": 90,
    "allowed_accounts": 10
  }
]
```

---

### 34. Create Subscription Type

Create a new subscription plan.

**Endpoint**: `POST /api/accounts/subscription-types/`

**Permissions**: Site Owner only

**Request Body**:
```json
{
  "name": "Annual Plan",
  "price": "1000.00",
  "duration_days": 365,
  "allowed_accounts": 20
}
```

---

### 35-36. Subscription Type Management

- `GET /api/accounts/subscription-types/<type_id>/` - Get details
- `PATCH /api/accounts/subscription-types/<type_id>/` - Update
- `DELETE /api/accounts/subscription-types/<type_id>/` - Delete

---

### 37-40. Payment Methods

Similar CRUD endpoints for payment methods:
- `GET /api/accounts/payment-methods/` - List all
- `POST /api/accounts/payment-methods/` - Create
- `GET /api/accounts/payment-methods/<id>/` - Get details
- `PATCH /api/accounts/payment-methods/<id>/` - Update
- `DELETE /api/accounts/payment-methods/<id>/` - Delete

---

### 41-44. Pet Types

Similar CRUD endpoints for pet types:
- `GET /api/owners/pet-types/` - List all
- `POST /api/owners/pet-types/` - Create
- `GET /api/owners/pet-types/<id>/` - Get details
- `PATCH /api/owners/pet-types/<id>/` - Update
- `DELETE /api/owners/pet-types/<id>/` - Delete

---

### 45-48. Marketing Channels

Similar CRUD endpoints for marketing channels:
- `GET /api/owners/marketing-channels/` - List all
- `POST /api/owners/marketing-channels/` - Create
- `GET /api/owners/marketing-channels/<id>/` - Get details
- `PATCH /api/owners/marketing-channels/<id>/` - Update
- `DELETE /api/owners/marketing-channels/<id>/` - Delete

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Resource deleted successfully |
| 205 | Reset Content | Logout successful |
| 400 | Bad Request | Validation error or bad data |
| 401 | Unauthorized | Authentication failed |
| 402 | Payment Required | Subscription expired |
| 403 | Forbidden | No permission to access resource |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error |

### Custom Error Codes

| Code | HTTP Status | Message |
|------|-------------|---------|
| `inactive_user` | 403 | Your account has been deactivated |
| `inactive_clinic` | 403 | Clinic is inactive or suspended |
| `subscription_expired` | 402 | Subscription has expired |
| `overlapping_subscription` | 400 | Subscription dates overlap |
| `suspended_clinic` | 403 | Clinic is suspended |
| `invalid_status_transition` | 400 | Invalid subscription status transition |
| `account_limit_exceeded` | 403 | Account limit exceeded for subscription |
| `pagination_bypass_not_allowed` | 403 | Pagination bypass not allowed. You must be a site owner to retrieve all data without pagination. |

### Error Response Format

```json
{
  "error": "Error message here",
  "detail": "More detailed information",
  "code": "error_code"
}
```

Or for field validation errors:

```json
{
  "field_name": ["Error message for this field"],
  "another_field": ["Another error message"]
}
```

---

## Rate Limiting

Not currently implemented. Recommended for production:
- 100 requests per minute for authenticated users
- 20 requests per minute for unauthenticated endpoints

---

## Versioning

Current API version: **v1**

API versioning via URL prefix is recommended for future updates:
```
/api/v1/accounts/
/api/v2/accounts/  (future)
```

---

## Best Practices

### 1. Always Check Status Codes
Don't rely solely on HTTP 200. Check the actual status code and handle errors appropriately.

### 2. Store Tokens Securely
- Never store tokens in localStorage (XSS vulnerable)
- Use httpOnly cookies or secure storage solutions

### 3. Handle Token Expiry
Implement token refresh logic before access token expires.

### 4. Validate Input on Frontend
Provide immediate feedback to users before making API calls.

### 5. Log Errors
Log all API errors for debugging and monitoring.

---

## Support

For API issues or questions:
- Check error messages and codes
- Review this documentation
- Contact development team

---

**Last Updated**: October 24, 2024  
**API Version**: 1.0.0
