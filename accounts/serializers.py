#accounts/serializers.py

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework import serializers
from datetime import date, timedelta
from .models import User, Country, ClinicOwnerProfile, DoctorProfile, ReceptionProfile, SubscriptionType, PaymentMethod, SubscriptionHistory

from django.db.models import Q

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['role'] = user.role
        token['username'] = user.username
        
        return token

    def validate(self, attrs):
        # Run a subscription status check for all clinics on every login.
        # This is an alternative to a cron job running a management command.
        today = date.today()

        # 1. Handle newly active subscriptions
        upcoming_to_activate = SubscriptionHistory.objects.filter(
            status=SubscriptionHistory.Status.UPCOMING,
            start_date__lte=today
        )
        for sub in upcoming_to_activate:
            # Deactivate any other currently active subscription for the same clinic
            SubscriptionHistory.objects.filter(
                clinic=sub.clinic, status=SubscriptionHistory.Status.ACTIVE
            ).update(status=SubscriptionHistory.Status.ENDED)

            # Activate the new subscription and the clinic
            sub.status = SubscriptionHistory.Status.ACTIVE
            sub.save()
            sub.clinic.status = ClinicOwnerProfile.Status.ACTIVE
            sub.clinic.save()

        # 2. Handle expired subscriptions
        expired_subscriptions = SubscriptionHistory.objects.filter(
            status=SubscriptionHistory.Status.ACTIVE,
            end_date__lt=today
        )
        for sub in expired_subscriptions:
            sub.status = SubscriptionHistory.Status.ENDED
            sub.save()
            # If the clinic has no other active or upcoming subscriptions, set its status to ENDED
            if not sub.clinic.subscription_history.filter(Q(status=SubscriptionHistory.Status.ACTIVE) | Q(status=SubscriptionHistory.Status.UPCOMING)).exists():
                sub.clinic.status = ClinicOwnerProfile.Status.ENDED
                sub.clinic.save()

        data = super().validate(attrs)
        user = self.user

        # Check if the user's own account is active
        if not user.is_active:
            raise serializers.ValidationError("User account is inactive.", code='authorization')

        # Check the clinic's active status for all clinic-related roles
        clinic_profile = None
        if hasattr(user, 'clinic_owner_profile'):
            clinic_profile = user.clinic_owner_profile
        elif hasattr(user, 'doctor_profile') or hasattr(user, 'reception_profile'):
            profile = getattr(user, 'doctor_profile', None) or getattr(user, 'reception_profile', None)
            if profile:
                clinic_profile = profile.clinic_owner_profile

        clinic_is_active = clinic_profile.is_active if clinic_profile else True
        if not clinic_is_active:
            raise serializers.ValidationError(
                "The clinic this account is associated with is inactive. Please contact support.", code='authorization'
            )

        data['role'] = user.role

        # Add clinic_name to the response data
        clinic_name = "Vetalyze"  # Default for Admin/Site Owner
        if clinic_profile:
            clinic_name = clinic_profile.clinic_name
        
        data['clinic_name'] = clinic_name
        return data


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Customizes the token refresh response to include user role and clinic name,
    similar to the login response.
    """
    def validate(self, attrs):
        # The default `validate` method now returns both a new access token and a new
        # refresh token, because `ROTATE_REFRESH_TOKENS` is set to `True`. The old
        # refresh token is automatically blacklisted.
        data = super().validate(attrs)
        
        # The `super().validate()` call returns a new access and refresh token.
        # We can decode the new access token to get the user's ID.
        from rest_framework_simplejwt.tokens import AccessToken
        new_access_token = AccessToken(data['access'])
        user_id = new_access_token.payload.get('user_id')
        user = User.objects.get(id=user_id)

        # Check if the user's own account is active
        if not user.is_active:
            raise serializers.ValidationError("User account is inactive.", code='authorization')

        # Check the clinic's active status for all clinic-related roles
        clinic_profile = None
        if hasattr(user, 'clinic_owner_profile'):
            clinic_profile = user.clinic_owner_profile
        elif hasattr(user, 'doctor_profile') or hasattr(user, 'reception_profile'):
            # DoctorProfile and ReceptionProfile have a 'clinic_owner_profile' FK
            profile = getattr(user, 'doctor_profile', None) or getattr(user, 'reception_profile', None)
            if profile:
                clinic_profile = profile.clinic_owner_profile

        if clinic_profile and not clinic_profile.is_active:
            raise serializers.ValidationError(
                "The clinic this account is associated with is inactive. Please contact support.", code='authorization'
            )

        data['role'] = user.role
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
        fields = ['id', 'subscription_type', 'payment_method', 'activated_by', 'days_left', 'extra_accounts_number', 'ref_number', 'amount_paid', 'comments', 'activation_date', 'start_date', 'end_date', 'status', 'clinic']


class ClinicOwnerProfileSerializer(serializers.ModelSerializer):
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
            'user', 'country', 'country_id', 'clinic_owner_name',
            'clinic_name', 'owner_phone_number', 'clinic_phone_number', 'location',
            'facebook', 'website', 'instagram', 'tiktok', 'gmail', 'days_left',
            'added_by', 'joined_date', 'status', 'current_plan', 'subscription_history'
        ]
        read_only_fields = ['joined_date', 'added_by', 'current_plan', 'subscription_history', 'days_left']

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
        if view and view.action == 'list':
            ret.pop('subscription_history', None)
        return ret

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['role'] = User.Role.CLINIC_OWNER
        user = UserSerializer().create(validated_data=user_data)
        
        # The 'added_by' field is expected to be passed in from the view.
        profile = ClinicOwnerProfile.objects.create(user=user, **validated_data)
        return profile

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
        Check for overlapping subscriptions.
        """
        clinic_profile = self.context['clinic_profile']

        if clinic_profile.status == ClinicOwnerProfile.Status.SUSPENDED:
            raise serializers.ValidationError("Cannot create a new subscription for a suspended clinic. Please reactivate it first.")

        start_date = data['start_date']
        subscription_type = data['subscription_type']
        end_date = start_date + timedelta(days=subscription_type.duration_days)

        # Check for any subscriptions that are not in a 'final' state (ENDED or REFUNDED) and would overlap.
        # A SUSPENDED subscription should block the creation of a new one.
        overlapping_subscriptions = SubscriptionHistory.objects.filter(
            clinic=clinic_profile,
            end_date__gte=start_date,
            start_date__lte=end_date
        ).exclude(status__in=[SubscriptionHistory.Status.ENDED, SubscriptionHistory.Status.REFUNDED])

        if overlapping_subscriptions.exists():
            raise serializers.ValidationError("An active or upcoming subscription already exists that overlaps with this date range. Please ensure the start date is after any existing plan's end date.")

        return data

    def create(self, validated_data):
        # clinic and activated_by are set in the view
        clinic_profile = self.context['clinic_profile']
        activated_by_user = self.context['request'].user

        # If the new subscription starts today (making it active), end any currently active subscription.
        # We no longer delete upcoming subscriptions, allowing multiple to be queued.
        if validated_data['start_date'] <= date.today():
            SubscriptionHistory.objects.filter(clinic=clinic_profile, status=SubscriptionHistory.Status.ACTIVE).update(status=SubscriptionHistory.Status.ENDED)

        # Create the new subscription history
        subscription = SubscriptionHistory.objects.create(clinic=clinic_profile, activated_by=activated_by_user, **validated_data)

        # Update the clinic's status to ACTIVE if the new subscription is active now
        if subscription.status == SubscriptionHistory.Status.ACTIVE:
            clinic_profile.status = ClinicOwnerProfile.Status.ACTIVE
            clinic_profile.save()
        
        return subscription


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
