from rest_framework import viewsets
from .models import Owner, Pet, PetType, SocialMedia
from .serializers import OwnerSerializer, PetSerializer, PetTypeSerializer, SocialMediaSerializer
from accounts.permissions import IsClinicOwner, IsDoctor, IsReception

class OwnerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Owners (clients).
    - Clinic staff can view and manage owners associated with their clinic.
    """
    serializer_class = OwnerSerializer

    def get_queryset(self):
        # Filter owners by the clinic of the logged-in user
        user = self.request.user
        if hasattr(user, 'clinic_owner_profile'):
            return Owner.objects.filter(clinic=user.clinic_owner_profile)
        # Add logic for doctors/receptionists if they are linked to a clinic
        return Owner.objects.none()

    def get_serializer_context(self):
        # Pass request to serializer to get the user's clinic
        return {'request': self.request}

class PetTypeViewSet(viewsets.ModelViewSet):
    queryset = PetType.objects.all()
    serializer_class = PetTypeSerializer
    permission_classes = [IsClinicOwner | IsDoctor | IsReception] # Or more specific permissions

class SocialMediaViewSet(viewsets.ModelViewSet):
    queryset = SocialMedia.objects.all()
    serializer_class = SocialMediaSerializer
    permission_classes = [IsClinicOwner | IsDoctor | IsReception]