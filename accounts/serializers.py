from django.contrib.auth.models import User
from rest_framework import serializers
from .models import BusDetails
from django.db import transaction
from rest_framework.validators import UniqueValidator
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from .tokens import custom_token_generator

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

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
    reg_number = serializers.CharField(
        validators=[UniqueValidator(queryset=BusDetails.objects.all())]
    )

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
        


from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.models import User
from rest_framework import serializers

class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=6, write_only=True)
    token = serializers.CharField(write_only=True)
    uidb64 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        token = attrs.get('token')
        uidb64 = attrs.get('uidb64')

        # --- DEBUG PRINTS ---
        print(f"DEBUG: Received UID: {uidb64}")
        print(f"DEBUG: Received Token: {token}")

        try:
            # 1. Decode UID & Get User
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
            print(f"DEBUG: Found User: {user.username}")

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid User Link")

        # 2. Check Token (using your custom generator)
        is_valid = custom_token_generator.check_token(user, token)
        print(f"DEBUG: Token Valid? {is_valid}")

        if not is_valid:
            raise serializers.ValidationError("Token is invalid or expired")

        # 3. Store user in attrs so 'save' can use it later
        attrs['user'] = user 
        
        # --- CRITICAL FIX: Return the DICTIONARY (attrs), not the User object ---
        return attrs 

    def save(self, **kwargs):
        # 4. Actual Password Reset Logic happens here
        password = self.validated_data['password']
        user = self.validated_data['user']
        
        user.set_password(password)
        user.save()
        return user