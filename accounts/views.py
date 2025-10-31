#accounts/views.py

from itertools import groupby
from datetime import date, timedelta
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.conf import settings
from django.db import transaction, models as django_models
from django.db.models import ProtectedError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    CustomTokenObtainPairSerializer, ClinicOwnerProfileSerializer, 
    CreateSubscriptionHistorySerializer, DoctorProfileSerializer, 
    ReceptionProfileSerializer, SubscriptionTypeSerializer, 
    PaymentMethodSerializer, ChangePasswordSerializer, 
    SubscriptionHistorySerializer, CustomTokenRefreshSerializer,
    CountrySerializer
)
from .models import User, ClinicOwnerProfile, DoctorProfile, ReceptionProfile, SubscriptionType, PaymentMethod, SubscriptionHistory, Country, UserSession
from .permissions import IsSiteOwner, IsClinicOwner, IsDoctor, IsReception
from .filters import ClinicOwnerProfileFilter
from .exceptions import InvalidSubscriptionStatusError, PaginationBypassError, CountryInUseError, ProtectedObjectInUseError
import logging

logger = logging.getLogger(__name__)

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
    An endpoint to blacklist a refresh token and clean up user session.
    On the client-side, the access and refresh tokens should be deleted upon a successful request.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            refresh_jti = str(token.get('jti', ''))
            
            # Blacklist the refresh token
            token.blacklist()
            
            # Delete the user's session
            if refresh_jti:
                deleted_count, _ = UserSession.objects.filter(
                    user=request.user,
                    refresh_token_jti=refresh_jti
                ).delete()
                
                if deleted_count > 0:
                    logger.info(f"User {request.user.username} logged out successfully (session deleted)")
                else:
                    logger.warning(f"User {request.user.username} logged out but no session found")
            else:
                logger.info(f"User {request.user.username} logged out successfully")
            
            return Response(
                {"message": "Successfully logged out."},
                status=status.HTTP_205_RESET_CONTENT
            )
            
        except Exception as e:
            logger.error(f"Logout error for user {request.user.username}: {str(e)}")
            return Response(
                {"error": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST
            )



class ClinicOwnerProfileListCreateView(generics.ListCreateAPIView):
    """
    - Site Owners can list all clinic profiles.
    - Site Owners can create a new clinic profile.
    """
    permission_classes = [IsSiteOwner]
    queryset = ClinicOwnerProfile.objects.select_related(
        'user', 'country'
    ).prefetch_related(
        django_models.Prefetch(
            'subscription_history',
            queryset=SubscriptionHistory.objects.select_related(
                'subscription_type', 'payment_method', 'activated_by'
            ).filter(status=SubscriptionHistory.Status.ACTIVE),
            to_attr='_active_subscription_cached'
        )
    ).order_by('-joined_date')
    serializer_class = ClinicOwnerProfileSerializer
    filterset_class = ClinicOwnerProfileFilter
    search_fields = [
        'clinic_name', 
        'clinic_owner_name', 
        'user__username', 
        'owner_phone_number', 
        'clinic_phone_number'
    ]


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
        django_models.Prefetch(
            'subscription_history',
            queryset=SubscriptionHistory.objects.select_related(
                'subscription_type', 'payment_method', 'activated_by'
            ).order_by('-activation_date')
        ),
        django_models.Prefetch(
            'subscription_history',
            queryset=SubscriptionHistory.objects.select_related(
                'subscription_type', 'payment_method', 'activated_by'
            ).filter(status=SubscriptionHistory.Status.ACTIVE),
            to_attr='_active_subscription_cached'
        )
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
    - Clinic owners can change their own password.
    - Site owners can change any clinic owner's password.
    """
    permission_classes = [IsSiteOwner | IsClinicOwner]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            profile = get_object_or_404(
                ClinicOwnerProfile.objects.select_related('user'),
                pk=self.kwargs['pk']
            )
        except Http404:
            return Response(
                {'error': 'Clinic profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user_to_update = profile.user

        # Security check - clinic owners can only change their own password
        if request.user.role == User.Role.CLINIC_OWNER and user_to_update != request.user:
            logger.warning(
                f"Unauthorized password change attempt by {request.user.username} "
                f"for user {user_to_update.username}"
            )
            return Response(
                {'error': 'You can only change your own password.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            new_password = serializer.validated_data['new_password']
            user_to_update.set_password(new_password)
            user_to_update.save(update_fields=['password'])
            
            logger.info(
                f"Password changed for user {user_to_update.username} by {request.user.username}"
            )
            
            return Response(
                {'message': 'Password changed successfully.'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Failed to change password for user {user_to_update.username}: {str(e)}")
            return Response(
                {'error': 'Failed to change password. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ManageSubscriptionStatusView(views.APIView):
    """
    An endpoint for Site Owners to manage a subscription's status.
    - POST with {"action": "suspend", "comment": "..."} to suspend an ACTIVE subscription.
    - POST with {"action": "reactivate", "comment": "..."} to reactivate a SUSPENDED subscription.
    """
    permission_classes = [IsSiteOwner]

    def post(self, request, *args, **kwargs):
        try:
            subscription = get_object_or_404(
                SubscriptionHistory.objects.select_related('clinic'),
                pk=self.kwargs['sub_pk'],
                clinic_id=self.kwargs['clinic_pk']
            )
        except Http404:
            return Response(
                {'error': 'Subscription not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        action = request.data.get('action')
        comment = request.data.get('comment', '').strip()

        # Validation
        if not action:
            return Response(
                {'error': 'Action is required. Use "suspend" or "reactivate".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not comment:
            return Response(
                {'error': f'A comment is required to {action} a subscription.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        clinic_profile = subscription.clinic

        if action == 'suspend':
            return self._handle_suspend(subscription, clinic_profile, comment, request.user)
        elif action == 'reactivate':
            return self._handle_reactivate(subscription, clinic_profile, comment, request.user)
        else:
            return Response(
                {'error': 'Invalid action. Use "suspend" or "reactivate".'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @transaction.atomic
    def _handle_suspend(self, subscription, clinic_profile, comment, user):
        """Handle subscription suspension with atomic transaction."""
        if subscription.status != SubscriptionHistory.Status.ACTIVE:
            raise InvalidSubscriptionStatusError('Only ACTIVE subscriptions can be suspended.')
        
        # Calculate remaining days to "freeze" them
        days_remaining = subscription.days_left

        if clinic_profile.subscription_history.filter(status=SubscriptionHistory.Status.UPCOMING).exists():
            return Response(
                {'error': 'Cannot suspend a subscription for a clinic that has an upcoming plan.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            # Create a new record for the suspension
            SubscriptionHistory.objects.create(
                subscription_group=subscription.subscription_group,
                clinic=clinic_profile,
                subscription_type=subscription.subscription_type,
                payment_method=subscription.payment_method,
                amount_paid=subscription.amount_paid,
                start_date=date.today(),
                end_date=subscription.end_date,
                status=SubscriptionHistory.Status.SUSPENDED,
                comments=f"Suspended: {comment}\n[Days Remaining: {days_remaining}]",
                activated_by=user
            )

            logger.info(
                f"Subscription {subscription.id} suspended by {user.username} "
                f"for clinic {clinic_profile.clinic_name}"
            )
            
            return Response(
                {'message': 'Subscription and clinic suspended successfully.'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Failed to suspend subscription {subscription.id}: {str(e)}")
            return Response(
                {'error': 'Failed to suspend subscription. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def _handle_reactivate(self, subscription, clinic_profile, comment, user):
        """Handle subscription reactivation with atomic transaction."""
        if subscription.status != SubscriptionHistory.Status.SUSPENDED:
            raise InvalidSubscriptionStatusError('Only SUSPENDED subscriptions can be reactivated.')
        
        # Extract the frozen days remaining from the comment
        days_remaining = 0
        try:
            # Find the part of the comment like "[Days Remaining: 25]"
            comment_lines = subscription.comments.split('\n')
            for line in comment_lines:
                if line.startswith('[Days Remaining:'):
                    days_remaining = int(line.split(':')[1].strip().strip(']'))
                    break
        except (ValueError, IndexError):
            # Fallback if parsing fails: use original end_date logic
            new_end_date = subscription.end_date
        else:
            new_end_date = date.today() + timedelta(days=days_remaining)

        try:
            # Create a new record for the activation
            SubscriptionHistory.objects.create(
                subscription_group=subscription.subscription_group,
                clinic=clinic_profile,
                subscription_type=subscription.subscription_type,
                payment_method=subscription.payment_method, # These fields are copied for audit trail
                amount_paid=subscription.amount_paid, # The original payment is what matters
                start_date=date.today(),
                end_date=new_end_date,
                status=SubscriptionHistory.Status.ACTIVE,
                comments=f"Reactivated: {comment}",
                activated_by=user
            )
            
            logger.info(
                f"Subscription {subscription.id} reactivated by {user.username} "
                f"for clinic {clinic_profile.clinic_name}"
            )
            
            return Response(
                {'message': 'Subscription and clinic reactivated successfully.'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Failed to reactivate subscription {subscription.id}: {str(e)}")
            return Response(
                {'error': 'Failed to reactivate subscription. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RefundSubscriptionView(views.APIView):
    """
    An endpoint for Site Owners to refund a subscription.
    - POST with {"comment": "Reason for refund."} to refund.
    - Only ACTIVE, SUSPENDED, or UPCOMING subscriptions can be refunded.
    """
    permission_classes = [IsSiteOwner]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            subscription = get_object_or_404(
                SubscriptionHistory.objects.select_related('clinic'),
                pk=self.kwargs['sub_pk'],
                clinic_id=self.kwargs['clinic_pk']
            )
        except Http404:
            return Response(
                {'error': 'Subscription not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        comment = request.data.get('comment', '').strip()

        if not comment:
            return Response(
                {'error': 'A comment is required to refund a subscription.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        refundable_statuses = [
            SubscriptionHistory.Status.ACTIVE,
            SubscriptionHistory.Status.SUSPENDED,
            SubscriptionHistory.Status.UPCOMING
        ]
        
        if subscription.status not in refundable_statuses:
            return Response(
                {
                    'error': f'Cannot refund a subscription with status "{subscription.status}". '
                             f'Only ACTIVE, SUSPENDED, or UPCOMING subscriptions can be refunded.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create a new, final record with REFUNDED status
            SubscriptionHistory.objects.create(
                subscription_group=subscription.subscription_group,
                clinic=subscription.clinic,
                subscription_type=subscription.subscription_type,
                payment_method=subscription.payment_method,
                amount_paid=subscription.amount_paid,
                start_date=subscription.start_date,
                end_date=subscription.end_date,
                status=SubscriptionHistory.Status.REFUNDED,
                comments=f"Refunded: {comment}",
                activated_by=request.user
            )

            # Check if the clinic has any other active or upcoming subscriptions
            clinic_profile = subscription.clinic
            has_active_or_upcoming = clinic_profile.subscription_history.filter(
                Q(status=SubscriptionHistory.Status.ACTIVE) | 
                Q(status=SubscriptionHistory.Status.UPCOMING)
            ).exists()
            
            logger.info(
                f"Subscription {subscription.id} refunded by {request.user.username} "
                f"for clinic {clinic_profile.clinic_name}"
            )
            
            return Response(
                {'message': 'Subscription has been refunded successfully.'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Failed to refund subscription {subscription.id}: {str(e)}")
            return Response(
                {'error': 'Failed to refund subscription. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SubscriptionHistoryListCreateView(generics.ListCreateAPIView):
    """
    - Site Owners can list subscription history for a clinic.
    - Site Owners can create a new subscription, which also activates the clinic.
    """
    permission_classes = [IsSiteOwner]

    class GroupedHistoryItemSerializer(SubscriptionHistorySerializer):
        """A serializer for items within the history group that excludes the redundant group UUID."""
        class Meta(SubscriptionHistorySerializer.Meta):
            # Exclude the subscription_group from the inner history items
            fields = [field for field in SubscriptionHistorySerializer.Meta.fields if field != 'subscription_group']
    
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

    def list(self, request, *args, **kwargs):
        """
        Custom list method to group subscription history by subscription_group.
        """
        queryset = self.get_queryset().order_by('subscription_group', '-activation_date')
        
        # Group records by the subscription_group UUID
        grouped_subscriptions = []
        for key, group in groupby(queryset, key=lambda x: x.subscription_group):
            
            # Serialize the records within the group
            serializer = self.GroupedHistoryItemSerializer(list(group), many=True)
            
            grouped_subscriptions.append({
                'subscription_group': key,
                'history': serializer.data
            })

        # Since we are grouping, we should order the groups themselves.
        # Let's sort by the most recent activation date within each group.
        grouped_subscriptions.sort(
            key=lambda g: g['history'][0]['activation_date'], reverse=True
        )

        # Manually apply pagination to the grouped list
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(grouped_subscriptions, request, view=self)
        if page is not None:
            return paginator.get_paginated_response(page)

        return Response(grouped_subscriptions) # Fallback for no pagination


class GlobalSubscriptionHistoryListView(generics.ListAPIView):
    """
    An endpoint for Site Owners to view all subscription history records,
    filterable by month and year of activation. Defaults to the current month.
    e.g., /api/accounts/subscriptions/history/?year=2025&month=10
    """
    permission_classes = [IsSiteOwner]
    serializer_class = SubscriptionHistorySerializer

    class GroupedHistoryItemSerializer(SubscriptionHistorySerializer):
        """A serializer for items within the history group that excludes the redundant group UUID."""
        class Meta(SubscriptionHistorySerializer.Meta):
            # Exclude the subscription_group from the inner history items
            fields = [field for field in SubscriptionHistorySerializer.Meta.fields if field != 'subscription_group']


    def get_queryset(self):
        """
        Filters the queryset based on 'year' and 'month' query parameters.
        Defaults to the current year and month if not provided.
        """
        try:
            year = int(self.request.query_params.get('year', date.today().year))
            month = int(self.request.query_params.get('month', date.today().month))
        except (ValueError, TypeError):
            today = date.today()
            year = today.year
            month = today.month

        return SubscriptionHistory.objects.filter(
            activation_date__year=year,
            activation_date__month=month
        ).select_related(
            'clinic', 'subscription_type', 'payment_method', 'activated_by'
        ).order_by('-activation_date')

    def list(self, request, *args, **kwargs):
        """
        Custom list method to group the global subscription history by subscription_group.
        """
        queryset = self.get_queryset().order_by('subscription_group', '-activation_date')

        # Group records by the subscription_group UUID
        grouped_subscriptions = []
        for key, group in groupby(queryset, key=lambda x: x.subscription_group):
            
            # Serialize the records within the group
            serializer = self.GroupedHistoryItemSerializer(list(group), many=True)
            
            grouped_subscriptions.append({
                'subscription_group': key,
                'history': serializer.data
            })

        # Sort the groups themselves by the most recent activation date within each group.
        grouped_subscriptions.sort(
            key=lambda g: g['history'][0]['activation_date'], reverse=True
        )

        # Manually apply pagination to the grouped list
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(grouped_subscriptions, request, view=self)
        if page is not None:
            return paginator.get_paginated_response(page)

        return Response(grouped_subscriptions) # Fallback for no pagination


class ActiveUpcomingSubscriptionListView(generics.ListAPIView):
    """
    An endpoint for Site Owners to get a list of all currently active and
    upcoming subscriptions across all clinics.
    """
    permission_classes = [IsSiteOwner]
    serializer_class = SubscriptionHistorySerializer
    queryset = SubscriptionHistory.objects.filter(
        status__in=[SubscriptionHistory.Status.ACTIVE, SubscriptionHistory.Status.UPCOMING]
    ).select_related(
        'clinic', 'subscription_type', 'payment_method', 'activated_by'
    ).order_by('end_date')


class DoctorProfileListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsClinicOwner]
    serializer_class = DoctorProfileSerializer
    search_fields = ['full_name', 'user__username', 'phone_number']

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
    search_fields = ['full_name', 'user__username', 'phone_number']

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
    queryset = SubscriptionType.objects.filter(is_active=True)
    serializer_class = SubscriptionTypeSerializer
    permission_classes = [IsSiteOwner] # Only Site Owners can manage subscription types

class SubscriptionTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubscriptionType.objects.all() # Show all for detail view, even inactive ones
    serializer_class = SubscriptionTypeSerializer
    permission_classes = [IsSiteOwner]

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ProtectedObjectInUseError("This subscription type cannot be deleted because it is used in subscription histories.")


class PaymentMethodListCreateView(generics.ListCreateAPIView):
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsSiteOwner] # Only Site Owners can manage payment methods

class PaymentMethodDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PaymentMethod.objects.all() # Show all for detail view
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsSiteOwner]

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ProtectedObjectInUseError("This payment method cannot be deleted because it is used in subscription histories.")


class CountryListCreateView(generics.ListCreateAPIView):
    """
    - Site Owners can list all countries.
    - Site Owners can create a new country.
    """
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsSiteOwner] # Only Site Owners can manage countries

class CountryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    - Site Owners can retrieve, update, or delete a specific country.
    """
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsSiteOwner] # Only Site Owners can manage countries

    def perform_destroy(self, instance):
        if instance.clinics.exists():
            raise CountryInUseError()
        instance.delete()
