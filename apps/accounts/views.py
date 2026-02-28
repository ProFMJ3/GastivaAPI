from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, UserUpdateSerializer

User = get_user_model()

@extend_schema(
    tags=['accounts'],
    description="Inscription d'un nouvel utilisateur. Le numéro de téléphone est requis, l'email est optionnel.",
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(response=UserSerializer, description="Inscription réussie"),
        400: OpenApiResponse(description="Données invalides - vérifiez les champs requis"),
    },
)
class RegisterView(generics.CreateAPIView):
    """
    Vue d'inscription - retourne les tokens JWT après création.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]  # Assurez-vous que c'est bien AllowAny
    authentication_classes = []  # Optionnel: désactive l'authentification pour cette vue
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Inscription réussie!'
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['accounts'],
    description="Connexion avec numéro de téléphone ou email.",
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(response=UserSerializer, description="Connexion réussie"),
        401: OpenApiResponse(description="Identifiants invalides - téléphone/email ou mot de passe incorrect"),
    },
)
class LoginView(generics.GenericAPIView):
    """
    Vue de connexion - accepte téléphone OU email comme username.
    """
    permission_classes = [permissions.AllowAny]  # Assurez-vous que c'est bien AllowAny
    authentication_classes = []  # Optionnel: désactive l'authentification pour cette vue
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Connexion réussie!'
        })

@extend_schema(
    tags=['accounts'],
    description="Récupération du profil de l'utilisateur connecté.",
    responses=UserSerializer,
)
class UserProfileView(generics.RetrieveAPIView):
    """
    Vue pour récupérer le profil de l'utilisateur connecté.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=['accounts'],
    description="Mise à jour du profil de l'utilisateur connecté.",
    request=UserUpdateSerializer,
    responses=UserSerializer,
)
class UserProfileUpdateView(generics.UpdateAPIView):
    """
    Vue pour mettre à jour le profil de l'utilisateur connecté.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserUpdateSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(UserSerializer(instance).data)