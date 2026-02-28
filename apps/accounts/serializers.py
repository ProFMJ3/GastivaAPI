from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Phone number is required, email is optional.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'phone_number', 'email', 'first_name', 'last_name',
            'role', 'password', 'password2', 'avatar'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'phone_number': {'required': True},
            'email': {'required': False, 'allow_null': True, 'allow_blank': True},
            'role': {'required': False, 'default': 'CLIENT'},
            'avatar': {'required': False},
        }

    def validate(self, attrs):
        # Vérifier que les mots de passe correspondent
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        
        # Si l'email est fourni, vérifier qu'il n'existe pas déjà
        if attrs.get('email'):
            if User.objects.filter(email=attrs['email']).exists():
                raise serializers.ValidationError({"email": "Cet email est déjà utilisé."})
        
        # Vérifier que le téléphone n'existe pas déjà
        if User.objects.filter(phone_number=attrs['phone_number']).exists():
            raise serializers.ValidationError({"phone_number": "Ce numéro de téléphone est déjà utilisé."})
        
        return attrs

    def create(self, validated_data):
        # Retirer password2 des données
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        # Si email est une chaîne vide, le mettre à None
        if validated_data.get('email') == '':
            validated_data['email'] = None
        
        # Générer un username unique à partir du téléphone
        username = f"user_{validated_data['phone_number']}"
        
        # Vérifier si ce username existe déjà (au cas où)
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        
        # Créer l'utilisateur avec un username valide
        user = User.objects.create_user(
            username=username,
            password=password,
            **validated_data
        )
        
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for login - accepts phone OR email.
    """
    username = serializers.CharField(required=True, help_text="Numéro de téléphone ou email")
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            from django.contrib.auth import authenticate
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )

            if not user:
                msg = "Impossible de se connecter avec ces identifiants."
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Veuillez fournir un numéro/email et un mot de passe.'
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user details.
    """
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'role', 'avatar', 'is_verified', 'is_active', 'preferred_payment_method',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'username', 'is_verified', 'is_active', 'created_at', 'updated_at']

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    """
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'avatar', 'preferred_payment_method'
        ]