#accounts/views.py

from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework import generics, views, status
from rest_framework.response import Response
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404, Http404
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


class LogoutView(views.APIView):
    """
    An endpoint to blacklist a refresh token.
    On the client-side, the access and refresh tokens should be deleted upon a successful request.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)



class ClinicOwnerProfileListCreateView(generics.ListCreateAPIView):
    """
    - Site Owners can list all clinic profiles.
    - Site Owners can create a new clinic profile.
    """
    permission_classes = [IsSiteOwner]
    queryset = ClinicOwnerProfile.objects.select_related(
        'user', 'country'
    ).prefetch_related(
        'subscription_history__subscription_type',
        'subscription_history__payment_method'
    )
    serializer_class = ClinicOwnerProfileSerializer

    def get_serializer_context(self):
        """Ensure the view is passed to the serializer context."""
        context = super().get_serializer_context()
        context['view'] = self
        return context

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)


class ClinicOwnerProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    - Site Owners can retrieve and update any clinic profile.
    - Clinic Owners can retrieve their own profile.
    """
    permission_classes = [IsSiteOwner | IsClinicOwner]
    queryset = ClinicOwnerProfile.objects.select_related(
        'user', 'country'
    ).prefetch_related(
        'subscription_history__subscription_type',
        'subscription_history__payment_method'
    )
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
        profile = get_object_or_404(ClinicOwnerProfile, pk=self.kwargs['pk'])
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


class SuspendClinicView(views.APIView):
    """
    An endpoint for Site Owners to suspend or reactivate a clinic.
    - POST with {"action": "suspend", "comment": "Reason for suspension."} to suspend.
    - POST with {"action": "reactivate", "comment": "Reason for reactivating."} to reactivate.
    """
    permission_classes = [IsSiteOwner]

    def post(self, request, *args, **kwargs):
        clinic_profile = get_object_or_404(ClinicOwnerProfile, pk=self.kwargs['pk'])
        action = request.data.get('action')

        if action == 'suspend':
            comment = request.data.get('comment')
            if not comment or not comment.strip():
                return Response({'error': 'A comment is required to suspend a clinic.'}, status=status.HTTP_400_BAD_REQUEST)

            if clinic_profile.status != ClinicOwnerProfile.Status.ACTIVE:
                return Response({'error': 'Only active clinics can be suspended.'}, status=status.HTTP_400_BAD_REQUEST)
            
            active_sub = clinic_profile.active_subscription
            if not active_sub:
                # This case should ideally not happen if status is ACTIVE
                return Response({'error': 'No active subscription found to suspend.'}, status=status.HTTP_400_BAD_REQUEST)

            # Update statuses
            clinic_profile.status = ClinicOwnerProfile.Status.SUSPENDED
            active_sub.status = SubscriptionHistory.Status.SUSPENDED
            active_sub.comments = f"Suspended: {comment}"
            
            clinic_profile.save()
            active_sub.save()
            
            return Response({'status': 'Clinic and subscription suspended.'}, status=status.HTTP_200_OK)

        elif action == 'reactivate':
            comment = request.data.get('comment')
            if not comment or not comment.strip():
                return Response({'error': 'A comment is required to reactivate a clinic.'}, status=status.HTTP_400_BAD_REQUEST)

            if clinic_profile.status != ClinicOwnerProfile.Status.SUSPENDED:
                return Response({'error': 'This clinic is not suspended.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # The subscription's own save method will handle status change back to ACTIVE
            suspended_sub = clinic_profile.subscription_history.filter(status=SubscriptionHistory.Status.SUSPENDED).first()
            if suspended_sub:
                suspended_sub.comments = f"Reactivated: {comment}"
                suspended_sub.save() # This will re-evaluate and set status to ACTIVE
            
            clinic_profile.status = ClinicOwnerProfile.Status.ACTIVE
            clinic_profile.save()
            return Response({'status': 'Clinic reactivated.'}, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid action. Use "suspend" or "reactivate" and provide a comment.'}, status=status.HTTP_400_BAD_REQUEST)


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
        return SubscriptionHistory.objects.filter(clinic_id=clinic_pk).select_related(
            'subscription_type', 'payment_method', 'activated_by'
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        clinic_profile = get_object_or_404(ClinicOwnerProfile, pk=self.kwargs['clinic_pk'])
        context['clinic_profile'] = clinic_profile
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
        return DoctorProfile.objects.filter(
            clinic_owner_profile=self.request.user.clinic_owner_profile
        ).select_related('user')


class DoctorProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsClinicOwner | IsDoctor]
    serializer_class = DoctorProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.CLINIC_OWNER:
            return DoctorProfile.objects.filter(clinic_owner_profile=user.clinic_owner_profile).select_related('user')
        elif user.role == User.Role.DOCTOR:
            return DoctorProfile.objects.filter(user=user).select_related('user')
        return DoctorProfile.objects.none()


class ReceptionProfileListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsClinicOwner]
    serializer_class = ReceptionProfileSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['clinic_owner_profile'] = self.request.user.clinic_owner_profile
        return context

    def get_queryset(self):
        return ReceptionProfile.objects.filter(
            clinic_owner_profile=self.request.user.clinic_owner_profile
        ).select_related('user')


class ReceptionProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsClinicOwner | IsReception]
    serializer_class = ReceptionProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.CLINIC_OWNER:
            return ReceptionProfile.objects.filter(clinic_owner_profile=user.clinic_owner_profile).select_related('user')
        elif user.role == User.Role.RECEPTION:
            return ReceptionProfile.objects.filter(user=user).select_related('user')
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
