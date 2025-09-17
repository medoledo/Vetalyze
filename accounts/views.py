from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework import viewsets, status
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, ClinicOwnerProfileSerializer, DoctorProfileSerializer, ReceptionProfileSerializer, SubscriptionTypeSerializer, PaymentMethodSerializer, ChangePasswordSerializer
from .models import User, ClinicOwnerProfile, DoctorProfile, ReceptionProfile, SubscriptionType, PaymentMethod
from .permissions import IsSiteOwner , IsClinicOwner, IsDoctor, IsReception


# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def public_key_view(request):
    """
    Provides the public key for JWT verification.
    """
    return Response({'public_key': settings.SIMPLE_JWT['VERIFYING_KEY']})

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class ClinicOwnerProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Clinic Owner Profiles.
    - Site Owners can list, retrieve, and create profiles.
    - Clinic Owners can retrieve their own profile and change their password.
    - A '/me/' endpoint is available for a clinic owner to access their own profile data.
    """
    queryset = ClinicOwnerProfile.objects.all()
    serializer_class = ClinicOwnerProfileSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'list', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsSiteOwner]
        elif self.action == 'change_password':
            self.permission_classes = [IsSiteOwner | IsClinicOwner]
        elif self.action in ['retrieve', 'me']:
            # Allow SiteOwner OR ClinicOwner for retrieve actions.
            # The object-level permission will ensure clinic owners can only see/edit their own.
            self.permission_classes = [IsSiteOwner | IsClinicOwner]
        else:
            # Default to deny for any other actions like 'destroy'.
            self.permission_classes = [IsAdminUser]
        return super(ClinicOwnerProfileViewSet, self).get_permissions()

    def get_object(self):
        """
        For detail views, ensure clinic owners can only access their own profile.
        """
        obj = super().get_object()
        if self.request.user.role == User.Role.CLINIC_OWNER and obj.user != self.request.user:
            self.permission_denied(self.request)
        return obj

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request, *args, **kwargs):
        # A clinic owner can only view their own profile data via this endpoint.
        self.kwargs['pk'] = request.user.pk
        return self.retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None):
        profile = self.get_object()
        user_to_update = profile.user
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            # The serializer's validation checks the current_password if required.
            user_to_update.set_password(serializer.validated_data['new_password'])
            user_to_update.save()
            return Response({'status': 'password set'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DoctorProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Doctor Profiles.
    - Clinic Owners can manage doctors within their clinic.
    - Doctors can view their own profile.
    """
    queryset = DoctorProfile.objects.all()
    serializer_class = DoctorProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.CLINIC_OWNER:
            return DoctorProfile.objects.filter(clinic_owner_profile__user=user)
        elif user.role == User.Role.DOCTOR:
            return DoctorProfile.objects.filter(user=user)
        return DoctorProfile.objects.none() # Or handle permissions differently


class ReceptionProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Reception Profiles.
    - Clinic Owners can manage receptionists within their clinic.
    - Receptionists can view their own profile.
    """
    queryset = ReceptionProfile.objects.all()
    serializer_class = ReceptionProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.CLINIC_OWNER:
            return ReceptionProfile.objects.filter(clinic_owner_profile__user=user)
        elif user.role == User.Role.RECEPTION:
            return ReceptionProfile.objects.filter(user=user)
        return ReceptionProfile.objects.none()

class SubscriptionTypeViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionType.objects.all()
    serializer_class = SubscriptionTypeSerializer
    permission_classes = [IsSiteOwner] # Only Site Owners can manage subscription types

class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsSiteOwner] # Only Site Owners can manage payment methods
