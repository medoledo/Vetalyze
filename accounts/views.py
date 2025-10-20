from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework import generics, views, status
from rest_framework.response import Response
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, ClinicOwnerProfileSerializer, CreateSubscriptionHistorySerializer, DoctorProfileSerializer, ReceptionProfileSerializer, SubscriptionTypeSerializer, PaymentMethodSerializer, ChangePasswordSerializer, SubscriptionHistorySerializer
from .models import User, ClinicOwnerProfile, DoctorProfile, ReceptionProfile, SubscriptionType, PaymentMethod, SubscriptionHistory
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


class ClinicOwnerProfileListCreateView(generics.ListCreateAPIView):
    """
    - Site Owners can list all clinic profiles.
    - Site Owners can create a new clinic profile.
    """
    permission_classes = [IsSiteOwner]
    queryset = ClinicOwnerProfile.objects.all()
    serializer_class = ClinicOwnerProfileSerializer

    def get_serializer_context(self):
        """Ensure the view is passed to the serializer context."""
        context = super().get_serializer_context()
        context['view'] = self
        return context

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)


class ClinicOwnerProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    - Site Owners can retrieve, update, or delete any clinic profile.
    - Clinic Owners can retrieve their own profile.
    """
    permission_classes = [IsSiteOwner | IsClinicOwner]
    queryset = ClinicOwnerProfile.objects.all()
    serializer_class = ClinicOwnerProfileSerializer

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if user.role == User.Role.CLINIC_OWNER and obj.user != user:
            self.permission_denied(self.request, message='You can only view your own profile.')
        return obj

    def perform_update(self, serializer):
        if self.request.user.role != User.Role.SITE_OWNER:
            self.permission_denied(self.request, message='You do not have permission to edit this profile.')
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role != User.Role.SITE_OWNER:
            self.permission_denied(self.request, message='You do not have permission to delete this profile.')
        # The user is deleted via the on_delete=CASCADE on the profile's user field
        instance.delete()


class ClinicOwnerProfileMeView(generics.RetrieveAPIView):
    """
    An endpoint for a clinic owner to access their own profile data.
    """
    permission_classes = [IsClinicOwner]
    serializer_class = ClinicOwnerProfileSerializer

    def get_object(self):
        return self.request.user.clinic_owner_profile


class ChangePasswordView(views.APIView):
    """
    An endpoint for changing a user's password.
    """
    permission_classes = [IsSiteOwner | IsClinicOwner]

    def post(self, request, *args, **kwargs):
        profile = ClinicOwnerProfile.objects.get(pk=self.kwargs['pk'])
        user_to_update = profile.user

        # Security check
        if request.user.role == User.Role.CLINIC_OWNER and user_to_update != request.user:
            return Response({'error': 'You can only change your own password.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user_to_update.set_password(serializer.validated_data['new_password'])
            user_to_update.save()
            return Response({'status': 'password set'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionHistoryListCreateView(generics.ListCreateAPIView):
    """
    - Site Owners can list subscription history for a clinic.
    - Site Owners can create a new subscription, which also activates the clinic.
    """
    permission_classes = [IsSiteOwner]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateSubscriptionHistorySerializer
        return SubscriptionHistorySerializer

    def get_queryset(self):
        clinic_pk = self.kwargs['clinic_pk']
        return SubscriptionHistory.objects.filter(clinic_id=clinic_pk)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['clinic_profile'] = ClinicOwnerProfile.objects.get(pk=self.kwargs['clinic_pk'])
        return context

    def perform_create(self, serializer):
        # The serializer's `create` method now handles all the logic,
        # including setting the clinic status and deactivating old subscriptions.
        serializer.save()


class DoctorProfileListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsClinicOwner]
    serializer_class = DoctorProfileSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['clinic_owner_profile'] = self.request.user.clinic_owner_profile
        return context

    def get_queryset(self):
        return DoctorProfile.objects.filter(clinic_owner_profile=self.request.user.clinic_owner_profile)


class DoctorProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsClinicOwner | IsDoctor]
    serializer_class = DoctorProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.CLINIC_OWNER:
            return DoctorProfile.objects.filter(clinic_owner_profile=user.clinic_owner_profile)
        elif user.role == User.Role.DOCTOR:
            return DoctorProfile.objects.filter(user=user)
        return DoctorProfile.objects.none()


class ReceptionProfileListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsClinicOwner]
    serializer_class = ReceptionProfileSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['clinic_owner_profile'] = self.request.user.clinic_owner_profile
        return context

    def get_queryset(self):
        return ReceptionProfile.objects.filter(clinic_owner_profile=self.request.user.clinic_owner_profile)


class ReceptionProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsClinicOwner | IsReception]
    serializer_class = ReceptionProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.CLINIC_OWNER:
            return ReceptionProfile.objects.filter(clinic_owner_profile=user.clinic_owner_profile)
        elif user.role == User.Role.RECEPTION:
            return ReceptionProfile.objects.filter(user=user)
        return ReceptionProfile.objects.none()


class SubscriptionTypeListCreateView(generics.ListCreateAPIView):
    queryset = SubscriptionType.objects.all()
    serializer_class = SubscriptionTypeSerializer
    permission_classes = [IsSiteOwner] # Only Site Owners can manage subscription types

class SubscriptionTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubscriptionType.objects.all()
    serializer_class = SubscriptionTypeSerializer
    permission_classes = [IsSiteOwner]


class PaymentMethodListCreateView(generics.ListCreateAPIView):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsSiteOwner] # Only Site Owners can manage payment methods

class PaymentMethodDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsSiteOwner]
