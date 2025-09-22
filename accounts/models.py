from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import timedelta
from django.core.validators import MinValueValidator
from django.conf import settings


class User(AbstractUser):
    """
    Custom User model inheriting from AbstractUser.
    This provides all the fields of the default User model,
    plus a 'role' field.
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


class Country(models.Model):
    """
    Stores country-specific settings and rules.
    """
    name = models.CharField(max_length=100, unique=True)
    max_id_number = models.PositiveIntegerField(default=14, validators=[MinValueValidator(1)])
    max_phone_number = models.PositiveIntegerField(default=11, validators=[MinValueValidator(1)])

    def __str__(self):
        return self.name


class ClinicOwnerProfile(models.Model):
    """
    Profile for users with the CLINIC_OWNER role.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='clinic_owner_profile',
        limit_choices_to={'role': User.Role.CLINIC_OWNER}
    )
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name='clinics')
    clinic_owner_name = models.CharField(max_length=255)
    national_id = models.CharField(max_length=50, blank=True)
    clinic_name = models.CharField(max_length=255)
    owner_phone_number = models.CharField(max_length=20, blank=True) 
    clinic_phone_number = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True)
    # Subscription details
    subscription_type = models.ForeignKey('SubscriptionType', on_delete=models.SET_NULL, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.SET_NULL, null=True, blank=True)
    subscription_start_date = models.DateField(null=True, blank=True)
    subscription_end_date = models.DateField(null=True, blank=True)
    # Clinic Social Media Links
    website_url = models.URLField(max_length=200, blank=True)
    facebook_url = models.URLField(max_length=200, blank=True)
    instagram_url = models.URLField(max_length=200, blank=True)
    tiktok_url = models.URLField(max_length=200, blank=True)
    is_active = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """
        Automatically calculate the subscription end date upon saving.
        """
        if self.subscription_type and self.subscription_start_date:
            self.subscription_end_date = self.subscription_start_date + timedelta(
                days=self.subscription_type.duration_days
            )
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.clinic_owner_name} - {self.clinic_name}"

    class Meta:
        # Ensures that a national_id is unique within a given country.
        unique_together = ('country', 'national_id')


class DoctorProfile(models.Model):
    """
    Profile for users with the DOCTOR role.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='doctor_profile',
        limit_choices_to={'role': User.Role.DOCTOR}
    )
    clinic_owner_profile = models.ForeignKey(
        ClinicOwnerProfile,
        on_delete=models.CASCADE,
        related_name='doctors'
    )
    full_name = models.CharField(max_length=255)
    national_id = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    birthday = models.DateField(null=True, blank=True)
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # You can add any doctor-specific fields here in the future.

    class Meta:
        # Ensures national_id is unique per clinic.
        unique_together = ('clinic_owner_profile', 'national_id')

    def __str__(self):
        return self.full_name


class ReceptionProfile(models.Model):
    """
    Profile for users with the RECEPTION role.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='reception_profile',
        limit_choices_to={'role': User.Role.RECEPTION}
    )
    clinic_owner_profile = models.ForeignKey(
        ClinicOwnerProfile,
        on_delete=models.CASCADE,
        related_name='receptionists'
    )
    full_name = models.CharField(max_length=255)
    national_id = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    birthday = models.DateField(null=True, blank=True)
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # You can add any reception-specific fields here in the future.

    class Meta:
        # Ensures national_id is unique per clinic.
        unique_together = ('clinic_owner_profile', 'national_id')

    def __str__(self):
        return self.full_name


class SubscriptionType(models.Model):
    """
    Defines the types of subscriptions available (e.g., Basic, Premium).
    """
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.IntegerField(help_text="Duration of the subscription in days.")
    allowed_accounts = models.PositiveIntegerField(default=5, help_text="Total number of Doctor/Reception accounts allowed.")

    def __str__(self):
        return f"{self.name} - {self.price} for {self.duration_days} days"


class PaymentMethod(models.Model):
    """
    Stores payment methods for clinic owners.
    """
    name = models.CharField(max_length=100, help_text="Name of the payment method (e.g., Visa, Cash)")

    def __str__(self):
        return self.name
