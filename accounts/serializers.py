from django.contrib.auth.models import User
from rest_framework import serializers
from .models import BusDetails
from django.db import transaction
from rest_framework.validators import UniqueValidator

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
    
class BusRegisterSerializer(serializers.ModelSerializer):
    # --- ADD VALIDATORS HERE ---
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    # ---------------------------
    password = serializers.CharField(write_only=True)
    bus_name = serializers.CharField()
    reg_number = serializers.CharField()

    class Meta:
        model = BusDetails
        fields = ['username', 'email', 'password', 'bus_name', 'reg_number']

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password']
            )
            
            bus_details = BusDetails.objects.create(
                user=user,
                bus_name=validated_data['bus_name'],
                reg_number=validated_data['reg_number']
            )
            return bus_details