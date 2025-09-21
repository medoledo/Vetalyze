from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
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
        data['role'] = self.user.role
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


class ClinicOwnerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = ClinicOwnerProfile
        fields = '__all__'

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
        user = self.context['request'].user
        if user.role != User.Role.SITE_OWNER:
            raise serializers.ValidationError("You do not have permission to edit profile details.")

        # Prevent changing the user or password via this method.
        validated_data.pop('user', None)

        # Update ClinicOwnerProfile fields
        instance.clinic_owner_name = validated_data.get('clinic_owner_name', instance.clinic_owner_name)
        instance.clinic_name = validated_data.get('clinic_name', instance.clinic_name)
        instance.owner_phone_number = validated_data.get('owner_phone_number', instance.owner_phone_number)
        instance.clinic_phone_number = validated_data.get('clinic_phone_number', instance.clinic_phone_number)
        instance.location = validated_data.get('location', instance.location)
        instance.email = validated_data.get('email', instance.email)
        instance.subscription_type = validated_data.get('subscription_type', instance.subscription_type)
        instance.amount_paid = validated_data.get('amount_paid', instance.amount_paid)
        instance.payment_method = validated_data.get('payment_method', instance.payment_method)
        instance.subscription_start_date = validated_data.get('subscription_start_date', instance.subscription_start_date)
        instance.subscription_end_date = validated_data.get('subscription_end_date', instance.subscription_end_date)
        instance.save()

        return instance

    def validate(self, data):
        """
        Validate phone numbers against the country's max length.
        """
        country = data.get('country')
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
        # The clinic_owner_profile is passed in the data during creation
        clinic_profile = self.initial_data.get('clinic_owner_profile')
        if clinic_profile:
            clinic = ClinicOwnerProfile.objects.get(pk=clinic_profile)
            country = clinic.country
            max_len = country.max_phone_number
            if value and len(value) > max_len:
                raise serializers.ValidationError(f"Phone number cannot exceed {max_len} digits for {country.name}.")
        return value

    def validate_national_id(self, value):
        clinic_profile = self.initial_data.get('clinic_owner_profile')
        if clinic_profile:
            clinic = ClinicOwnerProfile.objects.get(pk=clinic_profile)
            country = clinic.country
            max_len = country.max_id_number
            if value and len(value) > max_len:
                raise serializers.ValidationError(f"National ID cannot exceed {max_len} characters for {country.name}.")
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
        clinic_profile = self.initial_data.get('clinic_owner_profile')
        if clinic_profile:
            clinic = ClinicOwnerProfile.objects.get(pk=clinic_profile)
            country = clinic.country
            max_len = country.max_phone_number
            if value and len(value) > max_len:
                raise serializers.ValidationError(f"Phone number cannot exceed {max_len} digits for {country.name}.")
        return value

    def validate_national_id(self, value):
        clinic_profile = self.initial_data.get('clinic_owner_profile')
        if clinic_profile:
            clinic = ClinicOwnerProfile.objects.get(pk=clinic_profile)
            country = clinic.country
            max_len = country.max_id_number
            if value and len(value) > max_len:
                raise serializers.ValidationError(f"National ID cannot exceed {max_len} characters for {country.name}.")
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


class SubscriptionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionType
        fields = '__all__'


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'
