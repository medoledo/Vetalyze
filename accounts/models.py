from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom User model inheriting from AbstractUser.
    This provides all the fields of the default User model,
    plus any custom fields you add.
    """
    
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        SITE_OWNER = "SITE_OWNER", "Site Owner"
        CLINIC_OWNER = "CLINIC_OWNER", "Clinic Owner"
        DOCTOR = "DOCTOR", "Doctor"
        RECEPTION = "RECEPTION", "Reception"

    role = models.CharField(
        max_length=50, choices=Role.choices, default=Role.RECEPTION
    )
