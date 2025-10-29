#accounts/serializers.py

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework import serializers
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Q
from .models import User, Country, ClinicOwnerProfile, DoctorProfile, ReceptionProfile, SubscriptionType, PaymentMethod, SubscriptionHistory
from .exceptions import InactiveUserError, InactiveClinicError, OverlappingSubscriptionError, SuspendedClinicError
import logging

logger = logging.getLogger(__name__)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['role'] = user.role
        token['username'] = user.username
        
        return token

    def validate(self, attrs):
        """
        Validate login credentials and check user/clinic status.
        Note: Subscription status updates are now handled by a background task
        (management command: update_subscription_statuses) that runs daily at 12:01 AM.
        """
        data = super().validate(attrs)
        user = self.user

        # Check if the user's own account is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {user.username}")
            raise InactiveUserError("Your account has been deactivated. Please contact support.")

        # Check the clinic's active status for all clinic-related roles
        clinic_profile = None
        name = None

        if hasattr(user, 'clinic_owner_profile'):
            clinic_profile = user.clinic_owner_profile
            name = clinic_profile.clinic_owner_name
        elif hasattr(user, 'doctor_profile') or hasattr(user, 'reception_profile'):
            profile = getattr(user, 'doctor_profile', None) or getattr(user, 'reception_profile', None)
            if profile:
                clinic_profile = profile.clinic_owner_profile
                name = profile.full_name

        # Verify clinic status
        if clinic_profile:
            if not clinic_profile.is_active:
                logger.warning(
                    f"Login attempt for user {user.username} with inactive clinic: {clinic_profile.clinic_name if clinic_profile else 'N/A'}"
                )
                raise InactiveClinicError(
                    "The clinic associated with this account is inactive. Please contact support."
                )

        # Add custom data to the response
        data['role'] = user.role
        data['username'] = user.username
        data['name'] = name
        data['clinic_name'] = clinic_profile.clinic_name if clinic_profile else "Vetalyze"
        
        logger.info(f"Successful login for user: {user.username}")
        return data


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Customizes the token refresh response to include user role and clinic name,
    similar to the login response.
    """
    def validate(self, attrs):
        """
        Validate token refresh and check user/clinic status.
        """
        data = super().validate(attrs)
        
        # Decode the new access token to get the user's ID
        from rest_framework_simplejwt.tokens import AccessToken
        new_access_token = AccessToken(data['access'])
        user_id = new_access_token.payload.get('user_id')
        
        try:
            user = User.objects.select_related(
                'clinic_owner_profile',
                'doctor_profile__clinic_owner_profile',
                'reception_profile__clinic_owner_profile'
            ).get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.", code='authorization')

        # Check if the user's account is active
        if not user.is_active:
            logger.warning(f"Token refresh attempt for inactive user: {user.username}")
            raise InactiveUserError("Your account has been deactivated. Please contact support.")

        # Check the clinic's active status
        clinic_profile = None
        name = None

        if hasattr(user, 'clinic_owner_profile'):
            clinic_profile = user.clinic_owner_profile
            name = clinic_profile.clinic_owner_name
        elif hasattr(user, 'doctor_profile') or hasattr(user, 'reception_profile'):
            profile = getattr(user, 'doctor_profile', None) or getattr(user, 'reception_profile', None)
            if profile:
                clinic_profile = profile.clinic_owner_profile
                name = profile.full_name

        if clinic_profile and not clinic_profile.is_active:
            logger.warning(
                f"Token refresh for user {user.username} with inactive clinic: {clinic_profile.clinic_name}"
            )
            raise InactiveClinicError(
                "The clinic associated with this account is inactive. Please contact support."
            )

        # Add custom data to the response
        data['role'] = user.role
        data['username'] = user.username
        data['name'] = name
        data['clinic_name'] = clinic_profile.clinic_name if clinic_profile else "Vetalyze"
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'role')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            role=validated_data['role']
        )
        return user


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'


class SubscriptionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionType
        fields = '__all__'


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    subscription_type = SubscriptionTypeSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)
    activated_by = UserSerializer(read_only=True)
    days_left = serializers.IntegerField(read_only=True)

    class Meta:
        model = SubscriptionHistory
        fields = ['id', 'subscription_group', 'subscription_type', 'payment_method', 'activated_by', 'days_left', 'extra_accounts_number', 'ref_number', 'amount_paid', 'comments', 'activation_date', 'start_date', 'end_date', 'status', 'clinic']


class ClinicOwnerProfileSerializer(serializers.ModelSerializer):
    clinic_id = serializers.IntegerField(source='pk', read_only=True)
    user = UserSerializer()
    country = CountrySerializer(read_only=True)
    current_plan = SubscriptionTypeSerializer(read_only=True)
    added_by = serializers.StringRelatedField(read_only=True)
    subscription_history = SubscriptionHistorySerializer(many=True, read_only=True)
    days_left = serializers.SerializerMethodField()

    country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), source='country', write_only=True
    )

    class Meta:
        model = ClinicOwnerProfile
        fields = [
            'clinic_id', 'user', 'country', 'country_id', 'clinic_owner_name',
            'clinic_name', 'owner_phone_number', 'clinic_phone_number', 'location',
            'facebook', 'website', 'instagram', 'tiktok', 'gmail', 'days_left',
            'added_by', 'joined_date', 'status', 'current_plan', 'subscription_history'
        ]
        read_only_fields = ['clinic_id', 'joined_date', 'added_by', 'current_plan', 'subscription_history', 'days_left']

    def get_days_left(self, obj):
        """Calculate days left from the active subscription."""
        active_sub = obj.active_subscription
        if active_sub:
            return active_sub.days_left
        return None

    def to_representation(self, instance):
        """
        Exclude `subscription_history` for list views to keep the payload light.
        """
        ret = super().to_representation(instance)
        view = self.context.get('view')
        if view and getattr(view, 'action', None) == 'list':
            ret.pop('subscription_history', None)
        return ret

    @transaction.atomic
    def create(self, validated_data):
        """
        Create a new clinic owner profile with atomic transaction to ensure data integrity.
        """
        user_data = validated_data.pop('user')
        user_data['role'] = User.Role.CLINIC_OWNER
        
        try:
            # Create user account
            user = UserSerializer().create(validated_data=user_data)
            
            # Create clinic profile
            profile = ClinicOwnerProfile.objects.create(user=user, **validated_data)
            
            logger.info(f"Created clinic owner profile: {profile.clinic_name} (User: {user.username})")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to create clinic owner profile: {str(e)}")
            raise serializers.ValidationError(
                f"Failed to create clinic owner profile. Please try again or contact support."
            )

    def update(self, instance, validated_data):
        validated_data.pop('user', None)

        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()

        return instance

    def validate(self, data):
        """
        Validate phone numbers against the country's max length.
        """
        # On create, country is in data. On update, it's on the instance.
        country = data.get('country') or (self.instance and self.instance.country)
        if not country:
            # This can happen on create if country_id is not provided.
            raise serializers.ValidationError("Country is required.")
        max_len = country.max_phone_number

        owner_phone_number = data.get('owner_phone_number')
        if owner_phone_number and len(owner_phone_number) > max_len:
            raise serializers.ValidationError(f"Owner phone number cannot exceed {max_len} digits for {country.name}.")

        clinic_phone_number = data.get('clinic_phone_number')
        if clinic_phone_number and len(clinic_phone_number) > max_len:
            raise serializers.ValidationError(f"Clinic phone number cannot exceed {max_len} digits for {country.name}.")

        return data


class CreateSubscriptionHistorySerializer(serializers.ModelSerializer):
    """Serializer for creating a new subscription history record."""
    subscription_type_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionType.objects.all(), source='subscription_type'
    )
    payment_method_id = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethod.objects.all(), source='payment_method'
    )

    class Meta:
        model = SubscriptionHistory
        fields = [
            'subscription_type_id', 'payment_method_id', 'amount_paid', 'start_date',
            'ref_number', 'comments', 'extra_accounts_number'
        ]
        read_only_fields = ['end_date']

    def validate(self, data):
        """
        Validate subscription creation with comprehensive checks.
        """
        clinic_profile = self.context['clinic_profile']

        # Prevent creating subscriptions for suspended clinics
        if clinic_profile.status == ClinicOwnerProfile.Status.SUSPENDED:
            logger.warning(
                f"Attempt to create subscription for suspended clinic: {clinic_profile.clinic_name}"
            )
            raise SuspendedClinicError(
                "Cannot create a new subscription for a suspended clinic. Please reactivate it first."
            )

        start_date = data['start_date']
        subscription_type = data['subscription_type']
        end_date = start_date + timedelta(days=subscription_type.duration_days)

        # Validate start date is not in the past
        if start_date < date.today():
            raise serializers.ValidationError({
                "start_date": "Subscription start date cannot be in the past."
            })

        # Check for overlapping subscriptions
        overlapping_subscriptions = SubscriptionHistory.objects.filter(
            clinic=clinic_profile,
            end_date__gte=start_date,
            start_date__lte=end_date
        ).exclude(status__in=[SubscriptionHistory.Status.ENDED, SubscriptionHistory.Status.REFUNDED])

        if overlapping_subscriptions.exists():
            logger.warning(
                f"Overlapping subscription attempt for clinic: {clinic_profile.clinic_name}"
            )
            raise OverlappingSubscriptionError(
                "An active or upcoming subscription already exists that overlaps with this date range. "
                "Please ensure the start date is after any existing plan's end date."
            )

        # Validate amount paid
        if data.get('amount_paid', 0) < 0:
            raise serializers.ValidationError({
                "amount_paid": "Amount paid cannot be negative."
            })

        return data

    @transaction.atomic
    def create(self, validated_data):
        """
        Create a new subscription with atomic transaction to ensure data integrity.
        """
        clinic_profile = self.context['clinic_profile']
        activated_by_user = self.context['request'].user

        try:
            # If the new subscription starts today, end any currently active subscription
            if validated_data['start_date'] <= date.today():
                SubscriptionHistory.objects.filter(
                    clinic=clinic_profile,
                    status=SubscriptionHistory.Status.ACTIVE
                ).update(status=SubscriptionHistory.Status.ENDED)

            # Create the new subscription
            subscription = SubscriptionHistory.objects.create(
                clinic=clinic_profile,
                activated_by=activated_by_user,
                **validated_data
            )

            # Update clinic status if subscription is active
            if subscription.status == SubscriptionHistory.Status.ACTIVE:
                clinic_profile.status = ClinicOwnerProfile.Status.ACTIVE
                clinic_profile.save(update_fields=['status'])
            
            logger.info(
                f"Created subscription for clinic {clinic_profile.clinic_name}: "
                f"{subscription.subscription_type.name} (Status: {subscription.status})"
            )
            
            return subscription
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            raise serializers.ValidationError(
                "Failed to create subscription. Please try again or contact support."
            )


class DoctorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = DoctorProfile
        fields = '__all__'

    def validate_phone_number(self, value):
        """
        Validate phone number against the country's max length.
        """
        clinic_profile = self.context.get('clinic_owner_profile')
        if clinic_profile and value:
            max_len = clinic_profile.country.max_phone_number
            if len(value) > max_len:
                raise serializers.ValidationError(f"Phone number cannot exceed {max_len} digits for {clinic_profile.country.name}.")
        return value


class ReceptionProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ReceptionProfile
        fields = '__all__'

    def validate_phone_number(self, value):
        """
        Validate phone number against the country's max length.
        """
        clinic_profile = self.context.get('clinic_owner_profile')
        if clinic_profile and value:
            max_len = clinic_profile.country.max_phone_number
            if len(value) > max_len:
                raise serializers.ValidationError(f"Phone number cannot exceed {max_len} digits for {clinic_profile.country.name}.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for the password change endpoint.
    """
    current_password = serializers.CharField(required=False, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_new_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "The new passwords do not match."})
        return data

    def validate_current_password(self, value):
        user = self.context['request'].user
        # Clinic Owners must provide their current password, and it must be correct.
        if user.role == User.Role.CLINIC_OWNER:
            if not value:
                raise serializers.ValidationError("Current password is required.")
            if not user.check_password(value):
                raise serializers.ValidationError("Current password is not correct.")
        return value
