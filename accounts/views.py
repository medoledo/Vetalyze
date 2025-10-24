#accounts/views.py

from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework import generics, views, status
from rest_framework.response import Response
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404, Http404
from django.db.models import Q
from .serializers import CustomTokenObtainPairSerializer, ClinicOwnerProfileSerializer, CreateSubscriptionHistorySerializer, DoctorProfileSerializer, ReceptionProfileSerializer, SubscriptionTypeSerializer, PaymentMethodSerializer, ChangePasswordSerializer, SubscriptionHistorySerializer, CustomTokenRefreshSerializer
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


class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer


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


class ManageSubscriptionStatusView(views.APIView):
    """
    An endpoint for Site Owners to manage a subscription's status.
    - POST with {"action": "suspend", "comment": "..."} to suspend an ACTIVE subscription.
    - POST with {"action": "reactivate", "comment": "..."} to reactivate a SUSPENDED subscription.
    """
    permission_classes = [IsSiteOwner]

    def post(self, request, *args, **kwargs):
        from datetime import date, timedelta
        subscription = get_object_or_404(SubscriptionHistory, pk=self.kwargs['sub_pk'], clinic_id=self.kwargs['clinic_pk'])
        action = request.data.get('action')
        comment = request.data.get('comment')

        if not comment or not comment.strip():
            return Response({'error': f'A comment is required to {action} a subscription.'}, status=status.HTTP_400_BAD_REQUEST)

        clinic_profile = subscription.clinic

        if action == 'suspend':
            if subscription.status != SubscriptionHistory.Status.ACTIVE:
                return Response({'error': 'Only ACTIVE subscriptions can be suspended.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if clinic_profile.subscription_history.filter(status=SubscriptionHistory.Status.UPCOMING).exists():
                return Response({'error': 'Cannot suspend a subscription for a clinic that has an upcoming plan.'}, status=status.HTTP_400_BAD_REQUEST)

            # End the current active subscription
            original_end_date = subscription.end_date
            subscription.end_date = date.today() - timedelta(days=1)
            subscription.status = SubscriptionHistory.Status.ENDED
            subscription.comments = f"{subscription.comments}\nEnded due to suspension on {date.today()}.".strip()
            subscription.save()

            # Create a new record for the suspension
            SubscriptionHistory.objects.create(
                subscription_group=subscription.subscription_group, # Keep the same group
                clinic=clinic_profile,
                subscription_type=subscription.subscription_type,
                payment_method=subscription.payment_method,
                amount_paid=subscription.amount_paid, # Or 0 if this is a new transaction
                start_date=date.today(),
                end_date=original_end_date,
                status=SubscriptionHistory.Status.SUSPENDED,
                comments=f"Suspended: {comment}",
                activated_by=request.user
            )

            subscription.status = SubscriptionHistory.Status.SUSPENDED
            subscription.comments = f"Suspended: {comment}"
            clinic_profile.status = ClinicOwnerProfile.Status.SUSPENDED
            clinic_profile.save()
            return Response({'status': 'Subscription and clinic suspended.'}, status=status.HTTP_200_OK)

        elif action == 'reactivate':
            if subscription.status != SubscriptionHistory.Status.SUSPENDED:
                return Response({'error': 'Only SUSPENDED subscriptions can be reactivated.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # End the current suspended subscription
            original_end_date = subscription.end_date
            subscription.end_date = date.today() - timedelta(days=1)
            subscription.status = SubscriptionHistory.Status.ENDED
            subscription.comments = f"{subscription.comments}\nEnded due to reactivation on {date.today()}.".strip()
            subscription.save()

            # Create a new record for the activation
            new_active_sub = SubscriptionHistory.objects.create(
                subscription_group=subscription.subscription_group, # Keep the same group
                clinic=clinic_profile,
                subscription_type=subscription.subscription_type,
                payment_method=subscription.payment_method,
                amount_paid=subscription.amount_paid, # Or 0
                start_date=date.today(),
                end_date=original_end_date,
                status=SubscriptionHistory.Status.ACTIVE,
                comments=f"Reactivated: {comment}",
                activated_by=request.user
            )
            
            clinic_profile.status = ClinicOwnerProfile.Status.ACTIVE
            clinic_profile.save()
            return Response({'status': 'Subscription and clinic reactivated.'}, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid action. Use "suspend" or "reactivate".'}, status=status.HTTP_400_BAD_REQUEST)


class RefundSubscriptionView(views.APIView):
    """
    An endpoint for Site Owners to refund a subscription.
    - POST with {"comment": "Reason for refund."} to refund.
    - Only ACTIVE, SUSPENDED, or UPCOMING subscriptions can be refunded.
    """
    permission_classes = [IsSiteOwner]

    def post(self, request, *args, **kwargs):
        subscription = get_object_or_404(SubscriptionHistory, pk=self.kwargs['sub_pk'], clinic_id=self.kwargs['clinic_pk'])
        comment = request.data.get('comment')

        if not comment or not comment.strip():
            return Response({'error': 'A comment is required to refund a subscription.'}, status=status.HTTP_400_BAD_REQUEST)

        if subscription.status not in [SubscriptionHistory.Status.ACTIVE, SubscriptionHistory.Status.SUSPENDED, SubscriptionHistory.Status.UPCOMING]:
            return Response({'error': f'Cannot refund a subscription with status "{subscription.status}". Only ACTIVE, SUSPENDED, or UPCOMING subscriptions can be refunded.'}, status=status.HTTP_400_BAD_REQUEST)

        # Update the subscription
        subscription.status = SubscriptionHistory.Status.REFUNDED
        subscription.comments = f"Refunded: {comment}"
        subscription.save()

        # Check if the clinic has any other active or upcoming subscriptions.
        # If not, the clinic's status becomes ENDED.
        clinic_profile = subscription.clinic
        if not clinic_profile.subscription_history.filter(
            Q(status=SubscriptionHistory.Status.ACTIVE) | Q(status=SubscriptionHistory.Status.UPCOMING)
        ).exists():
            clinic_profile.status = ClinicOwnerProfile.Status.ENDED
            clinic_profile.save()

        return Response({'status': 'Subscription has been refunded.'}, status=status.HTTP_200_OK)


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


class DoctorProfileMeView(generics.RetrieveAPIView):
    """
    An endpoint for a doctor to access their own profile data.
    """
    permission_classes = [IsDoctor]
    serializer_class = DoctorProfileSerializer

    def get_object(self):
        try:
            return self.request.user.doctor_profile
        except DoctorProfile.DoesNotExist:
            raise Http404("Doctor profile not found for this user.")


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


class ReceptionProfileMeView(generics.RetrieveAPIView):
    """
    An endpoint for a receptionist to access their own profile data.
    """
    permission_classes = [IsReception]
    serializer_class = ReceptionProfileSerializer

    def get_object(self):
        try:
            return self.request.user.reception_profile
        except ReceptionProfile.DoesNotExist:
            raise Http404("Reception profile not found for this user.")


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
