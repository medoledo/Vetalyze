from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from datetime import date
from django.contrib.auth import authenticate
from .models import User, Country, ClinicOwnerProfile, DoctorProfile, ReceptionProfile, SubscriptionType, PaymentMethod


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['role'] = user.role
        token['username'] = user.username
        
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        # Check if the user's own account is active
        if not user.is_active:
            raise serializers.ValidationError("User account is inactive.", code='authorization')

        # Check the clinic's active status for all clinic-related roles
        clinic_is_active = True
        if user.role == User.Role.CLINIC_OWNER:
            if hasattr(user, 'clinic_owner_profile'):
                clinic_is_active = user.clinic_owner_profile.is_active
        elif user.role == User.Role.DOCTOR:
            if hasattr(user, 'doctor_profile'):
                clinic_is_active = user.doctor_profile.clinic_owner_profile.is_active
        elif user.role == User.Role.RECEPTION:
            if hasattr(user, 'reception_profile'):
                clinic_is_active = user.reception_profile.clinic_owner_profile.is_active

        if not clinic_is_active:
            raise serializers.ValidationError(
                "The clinic this account is associated with is inactive. Please contact support.", code='authorization'
            )

        data['role'] = user.role

        # Add clinic_name to the response data
        clinic_name = "Vetalyze" # Default for Admin/Site Owner
        if user.role == User.Role.CLINIC_OWNER:
            if hasattr(user, 'clinic_owner_profile'):
                clinic_name = user.clinic_owner_profile.clinic_name
        elif user.role == User.Role.DOCTOR:
            if hasattr(user, 'doctor_profile'):
                clinic_name = user.doctor_profile.clinic_owner_profile.clinic_name
        elif user.role == User.Role.RECEPTION:
            if hasattr(user, 'reception_profile'):
                clinic_name = user.reception_profile.clinic_owner_profile.clinic_name
        
        data['clinic_name'] = clinic_name
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


class ClinicOwnerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    country = CountrySerializer(read_only=True)
    subscription_type = SubscriptionTypeSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)
    
    # These fields are used for writing data (create/update) but won't be shown in the response.
    country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), source='country', write_only=True
    )
    subscription_type_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionType.objects.all(), source='subscription_type', write_only=True, allow_null=True, required=False
    )
    payment_method_id = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethod.objects.all(), source='payment_method', write_only=True, allow_null=True
    )

    class Meta:
        model = ClinicOwnerProfile
        fields = [
            'user', 'country', 'country_id', 'clinic_owner_name', 'national_id', 
            'clinic_name', 'owner_phone_number', 'clinic_phone_number', 'location', 'email', 
            'is_active', 'subscription_type', 'amount_paid', 'payment_method', 
            'subscription_start_date', 'website_url', 'facebook_url', 'instagram_url', 'tiktok_url',
            'subscription_end_date'
        ]
        read_only_fields = [
            'is_active', 'subscription_type', 'amount_paid', 'payment_method', 
            'subscription_start_date', 'subscription_end_date'
        ]

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        # Ensure the user being created has the correct role
        user_data['role'] = User.Role.CLINIC_OWNER
        user = UserSerializer().create(validated_data=user_data)
        
        # Create the profile linked to the new user
        profile = ClinicOwnerProfile.objects.create(user=user, **validated_data)
        return profile

    def update(self, instance, validated_data):
        # This update method is only for Site Owners to update profile details.
        # Password changes are handled by a separate endpoint.
        # Prevent changing the user or password via this method.
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

        national_id = data.get('national_id')
        max_id_len = country.max_id_number
        if national_id and len(national_id) > max_id_len:
            raise serializers.ValidationError(f"National ID cannot exceed {max_id_len} characters for {country.name}.")
        return data


class ClinicSubscriptionSerializer(serializers.Serializer):
    """
    Serializer for activating a clinic's subscription.
    """
    subscription_type_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionType.objects.all(), source='subscription_type', write_only=True
    )
    payment_method_id = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethod.objects.all(), source='payment_method', write_only=True
    )
    amount_paid = serializers.DecimalField(max_digits=8, decimal_places=2)

    def update(self, instance, validated_data):
        """
        Activates the clinic by setting subscription details.
        """
        instance.subscription_type = validated_data.get('subscription_type')
        instance.payment_method = validated_data.get('payment_method')
        instance.amount_paid = validated_data.get('amount_paid')
        
        # Set automatic fields
        instance.subscription_start_date = date.today()
        instance.is_active = True
        
        instance.save() # The model's save() method will calculate the end_date
        return instance


class DoctorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = DoctorProfile
        fields = '__all__'

    def create(self, validated_data):
        # This assumes user creation is handled separately or not needed at profile creation
        # For simplicity, we're creating the profile for an existing DOCTOR user.
        # You might want to expand this to create the user as well.
        profile = DoctorProfile.objects.create(**validated_data)
        return profile

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

    def validate_national_id(self, value):
        clinic_profile = self.context.get('clinic_owner_profile')
        if clinic_profile and value:
            max_len = clinic_profile.country.max_id_number
            if len(value) > max_len:
                raise serializers.ValidationError(f"National ID cannot exceed {max_len} characters for {clinic_profile.country.name}.")
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

    def validate_national_id(self, value):
        clinic_profile = self.context.get('clinic_owner_profile')
        if clinic_profile and value:
            max_len = clinic_profile.country.max_id_number
            if len(value) > max_len:
                raise serializers.ValidationError(f"National ID cannot exceed {max_len} characters for {clinic_profile.country.name}.")
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
