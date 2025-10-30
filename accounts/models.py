#accounts/models.py

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import date, timedelta
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils.translation import gettext_lazy as _


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
        max_length=50, choices=Role.choices, default=Role.RECEPTION, db_index=True
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
    
    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")


class ClinicOwnerProfile(models.Model):
    """
    Profile for users with the CLINIC_OWNER role.
    """
    class Status(models.TextChoices):
        INACTIVE = "INACTIVE", _("Inactive") # No subscriptions yet
        ACTIVE = "ACTIVE", _("Active")
        ENDED = "ENDED", _("Ended")
        SUSPENDED = "SUSPENDED", _("Suspended")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='clinic_owner_profile',
        limit_choices_to={'role': 'CLINIC_OWNER'}
    )
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name='clinics')
    clinic_owner_name = models.CharField(max_length=255, db_index=True)
    clinic_name = models.CharField(max_length=255, db_index=True)
    owner_phone_number = models.CharField(max_length=20, db_index=True)
    clinic_phone_number = models.CharField(max_length=20, db_index=True)
    location = models.CharField(max_length=255, blank=True)
    
    # Social and Contact Links
    facebook = models.URLField(max_length=200, blank=True, null=True)
    website = models.URLField(max_length=200, blank=True, null=True)
    instagram = models.URLField(max_length=200, blank=True, null=True)
    tiktok = models.URLField(max_length=200, blank=True, null=True)
    gmail = models.EmailField(blank=True, null=True)

    # Management and Status
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_clinics',
        limit_choices_to={'role': 'SITE_OWNER'}
    )
    joined_date = models.DateField(auto_now_add=True)

    @property
    def status(self):
        """
        Dynamically determines the clinic's status based on the latest
        subscription history record.
        """
        latest_subscription = self.subscription_history.order_by('-activation_date', '-pk').first()

        if not latest_subscription:
            return self.Status.INACTIVE

        # Map SubscriptionHistory status to ClinicOwnerProfile status
        status_map = {
            SubscriptionHistory.Status.ACTIVE: self.Status.ACTIVE,
            SubscriptionHistory.Status.SUSPENDED: self.Status.SUSPENDED,
        }
        # For ENDED, REFUNDED, UPCOMING, the clinic status is considered ENDED or INACTIVE until active.
        return status_map.get(latest_subscription.status, self.Status.ENDED)
        
    @property
    def active_subscription(self):
        """
        Returns the currently active subscription history record from the prefetched
        cache if available, or queries the database.
        """
        if hasattr(self, '_active_subscription_cached'):
            # The list will be empty or have one item due to the Prefetch query.
            return self._active_subscription_cached[0] if self._active_subscription_cached else None
        return self.subscription_history.filter(status=SubscriptionHistory.Status.ACTIVE).first()

    @property
    def current_plan(self):
        """Returns the SubscriptionType of the active subscription, or None."""
        active_sub = self.active_subscription
        if active_sub:
            return active_sub.subscription_type
        return None
    
    @property
    def is_active(self):
        """Property to check if the clinic's status is Active."""
        return self.status == self.Status.ACTIVE

    def __str__(self):
        return f"{self.clinic_owner_name} - {self.clinic_name}"


class DoctorProfile(models.Model):
    """
    Profile for users with the DOCTOR role.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='doctor_profile',
        limit_choices_to={'role': 'DOCTOR'}
    )
    clinic_owner_profile = models.ForeignKey(
        ClinicOwnerProfile,
        on_delete=models.CASCADE,
        related_name='doctors',
        db_index=True
    )
    full_name = models.CharField(max_length=255, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True, db_index=True)
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['clinic_owner_profile', 'is_active']),
        ]

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
        limit_choices_to={'role': 'RECEPTION'}
    )
    clinic_owner_profile = models.ForeignKey(
        ClinicOwnerProfile,
        on_delete=models.CASCADE,
        related_name='receptionists',
        db_index=True
    )
    full_name = models.CharField(max_length=255, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True, db_index=True)
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['clinic_owner_profile', 'is_active']),
        ]

    def __str__(self):
        return self.full_name


class SubscriptionHistory(models.Model):
    """
    Stores the subscription history for each clinic.
    """
    class Status(models.TextChoices):
        UPCOMING = "UPCOMING", _("Upcoming")
        ACTIVE = "ACTIVE", _("Active")
        ENDED = "ENDED", _("Ended")
        SUSPENDED = "SUSPENDED", _("Suspended")
        REFUNDED = "REFUNDED", _("Refunded")

    subscription_group = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True, help_text="Identifier to group related subscription records together.")
    clinic = models.ForeignKey(
        ClinicOwnerProfile,
        on_delete=models.CASCADE,
        related_name='subscription_history'
    )
    subscription_type = models.ForeignKey('SubscriptionType', on_delete=models.PROTECT)
    extra_accounts_number = models.PositiveIntegerField(default=0)
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.PROTECT)
    ref_number = models.CharField(max_length=100, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activated_subscriptions',
        limit_choices_to={'role': 'SITE_OWNER'}
    )
    comments = models.TextField(blank=True)
    activation_date = models.DateField(auto_now_add=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, db_index=True) # Will be auto-populated
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPCOMING, db_index=True)

    @property
    def days_left(self):
        """Calculates the number of days remaining for the subscription."""
        if self.end_date and self.status == self.Status.ACTIVE:
            today = date.today()
            delta = self.end_date - today
            return max(0, delta.days)
        return 0

    def save(self, *args, **kwargs):
        """
        - Automatically calculate the end_date based on subscription duration.
        - Automatically set the status based on the start_date.
        """
        # Calculate end_date on creation if it's not set
        if not self.end_date and self.subscription_type:
            self.end_date = self.start_date + timedelta(days=self.subscription_type.duration_days)

        # On creation, determine if the subscription should be UPCOMING or ACTIVE
        # based on its start date, unless a specific status is already provided.
        if self.pk is None and self.status == self.Status.UPCOMING:
            today = date.today()
            if self.start_date > today:
                self.status = self.Status.UPCOMING
            else:
                self.status = self.Status.ACTIVE
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['clinic', 'status']),
            models.Index(fields=['status', 'end_date']),
            models.Index(fields=['activation_date', 'clinic']),
        ]

    def __str__(self):
        return f"{self.clinic.clinic_name} - {self.subscription_type.name} ({self.status})"


class SubscriptionType(models.Model):
    """
    Defines the types of subscriptions available (e.g., Basic, Premium).
    """
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.IntegerField(help_text="Duration of the subscription in days.")
    allowed_accounts = models.PositiveIntegerField(default=5, help_text="Total number of Doctor/Reception accounts allowed.")
    is_active = models.BooleanField(default=True, help_text="Designates whether this plan can be assigned to new subscriptions.")

    def __str__(self):
        return f"{self.name} - {self.price} for {self.duration_days} days"


class PaymentMethod(models.Model):
    """
    Stores payment methods for clinic owners.
    """
    name = models.CharField(max_length=100, help_text="Name of the payment method (e.g., Visa, Cash)")
    is_active = models.BooleanField(default=True, help_text="Designates whether this payment method is available for new transactions.")

    def __str__(self):
        return self.name
