from rest_framework import serializers
from .models import Owner, Pet, PetType, MarketingChannel

class PetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetType
        fields = '__all__'

class MarketingChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingChannel
        fields = '__all__'

class PetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = ['id', 'name', 'code', 'birthday', 'type']
        read_only_fields = ['code']

class OwnerSerializer(serializers.ModelSerializer):
    pets = PetSerializer(many=True)

    class Meta:
        model = Owner
        fields = ['id', 'full_name', 'phone_number', 'second_phone_number', 'code', 'knew_us_from', 'pets']
        read_only_fields = ['code']

    def create(self, validated_data):
        from django.db import transaction
        
        pets_data = validated_data.pop('pets')
        if not pets_data:
            raise serializers.ValidationError("An owner must have at least one pet.")
            
        # Get the clinic from the request context (will be set in the view)
        clinic = self.context['request'].user.clinic_owner_profile
        
        with transaction.atomic():
            owner = Owner.objects.create(clinic=clinic, **validated_data)
            
            # Bulk create pets for better performance
            pets_to_create = [Pet(owner=owner, **pet_data) for pet_data in pets_data]
            Pet.objects.bulk_create(pets_to_create)

        return owner

    def validate(self, data):
        """
        Validate phone numbers against the country's max length.
        """
        clinic = self.context['request'].user.clinic_owner_profile
        country = clinic.country
        max_len = country.max_phone_number

        phone_number = data.get('phone_number')
        if phone_number and len(phone_number) > max_len:
            raise serializers.ValidationError(f"Phone number cannot exceed {max_len} digits for {country.name}.")

        second_phone_number = data.get('second_phone_number')
        if second_phone_number and len(second_phone_number) > max_len:
            raise serializers.ValidationError(f"Second phone number cannot exceed {max_len} digits for {country.name}.")

        return data