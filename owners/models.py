from django.db import models
from accounts.models import ClinicOwnerProfile
import uuid

# Create your models here.

class MarketingChannel(models.Model):
    """
    Stores the different social media platforms or other channels
    where a client might have heard about the clinic.
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class PetType(models.Model):
    """
    Defines the type of a pet (e.g., Dog, Cat, Bird).
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Owner(models.Model):
    """
    Represents a client of a clinic.
    """
    clinic = models.ForeignKey(ClinicOwnerProfile, on_delete=models.CASCADE, related_name='owners', db_index=True)
    full_name = models.CharField(max_length=255, db_index=True)
    phone_number = models.CharField(max_length=20, db_index=True)
    second_phone_number = models.CharField(max_length=20, blank=True, null=True)
    code = models.CharField(max_length=7, unique=True, editable=False, db_index=True)
    knew_us_from = models.ForeignKey(MarketingChannel, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            # Generate a unique 7-character code, ensuring it's not already in use.
            # Using a limited retry to avoid infinite loops
            max_attempts = 10
            for _ in range(max_attempts):
                code = uuid.uuid4().hex[:7].upper()
                if not Owner.objects.filter(code=code).exists():
                    self.code = code
                    break
            else:
                # If we couldn't find a unique code after max_attempts, use a longer code
                self.code = uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['clinic', 'full_name']),
            models.Index(fields=['clinic', 'phone_number']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.code})"

class Pet(models.Model):
    """
    Represents a pet belonging to an owner.
    """
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='pets', db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    code = models.CharField(max_length=7, unique=True, editable=False, db_index=True)
    birthday = models.DateField(null=True, blank=True)
    type = models.ForeignKey(PetType, on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        if not self.code:
            # Generate a unique 7-character code, ensuring it's not already in use.
            # Using a limited retry to avoid infinite loops
            max_attempts = 10
            for _ in range(max_attempts):
                code = uuid.uuid4().hex[:7].upper()
                if not Pet.objects.filter(code=code).exists():
                    self.code = code
                    break
            else:
                # If we couldn't find a unique code after max_attempts, use a longer code
                self.code = uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.type.name})"
