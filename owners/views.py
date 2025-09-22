from rest_framework import generics
from .models import Owner, PetType, MarketingChannel
from .serializers import OwnerSerializer, PetTypeSerializer, MarketingChannelSerializer
from accounts.permissions import IsClinicOwner, IsDoctor, IsReception
from accounts.models import User

class OwnerListCreateView(generics.ListCreateAPIView):
    """
    - List all clients for the logged-in clinic owner.
    - Create a new client for the logged-in clinic owner.
    """
    permission_classes = [IsClinicOwner]
    serializer_class = OwnerSerializer

    def get_queryset(self):
        user = self.request.user
        # Clinic owners can see all clients in their clinic.
        if user.role == User.Role.CLINIC_OWNER:
            return Owner.objects.filter(clinic=user.clinic_owner_profile).prefetch_related('pets')
        return Owner.objects.none()

    def get_serializer_context(self):
        return {'request': self.request}


class OwnerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    - Retrieve, update, or delete a specific client.
    """
    permission_classes = [IsClinicOwner]
    serializer_class = OwnerSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.CLINIC_OWNER:
            return Owner.objects.filter(clinic=user.clinic_owner_profile)
        return Owner.objects.none()


class PetTypeListCreateView(generics.ListCreateAPIView):
    queryset = PetType.objects.all()
    serializer_class = PetTypeSerializer
    permission_classes = [IsClinicOwner | IsDoctor | IsReception]


class PetTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PetType.objects.all()
    serializer_class = PetTypeSerializer
    permission_classes = [IsClinicOwner | IsDoctor | IsReception]


class MarketingChannelListCreateView(generics.ListCreateAPIView):
    queryset = MarketingChannel.objects.all()
    serializer_class = MarketingChannelSerializer
    permission_classes = [IsClinicOwner | IsDoctor | IsReception]


class MarketingChannelDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MarketingChannel.objects.all()
    serializer_class = MarketingChannelSerializer
    permission_classes = [IsClinicOwner | IsDoctor | IsReception]