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
    clinic = models.ForeignKey(ClinicOwnerProfile, on_delete=models.CASCADE, related_name='owners')
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    second_phone_number = models.CharField(max_length=20, blank=True, null=True)
    code = models.CharField(max_length=7, unique=True, editable=False)
    knew_us_from = models.ForeignKey(MarketingChannel, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            # Generate a unique 7-character code, ensuring it's not already in use.
            while True:
                code = uuid.uuid4().hex[:7].upper()
                if not Owner.objects.filter(code=code).exists():
                    self.code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.code})"

class Pet(models.Model):
    """
    Represents a pet belonging to an owner.
    """
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=7, unique=True, editable=False)
    birthday = models.DateField(null=True, blank=True)
    type = models.ForeignKey(PetType, on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        if not self.code:
            # Generate a unique 7-character code, ensuring it's not already in use.
            while True:
                code = uuid.uuid4().hex[:7].upper()
                if not Pet.objects.filter(code=code).exists():
                    self.code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.type.name})"
