from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, UserUpdateSerializer
from rest_framework.views import APIView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone 
import os
from apps.orders.models import Order
from apps.reviews.models import Review

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
    


@extend_schema(
    tags=['accounts'],
    description="Upload d'avatar pour l'utilisateur connecté.",
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'avatar': {'type': 'string', 'format': 'binary'}
            }
        }
    },
    responses={
        200: OpenApiResponse(description="Avatar mis à jour"),
        400: OpenApiResponse(description="Aucun fichier fourni"),
    },
)
class AvatarUploadView(APIView):
    """Uploader un avatar"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if 'avatar' not in request.FILES:
            return Response(
                {'error': 'Aucun fichier fourni'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        avatar = request.FILES['avatar']
        user = request.user
        
        # Supprimer l'ancien avatar s'il existe
        if user.avatar:
            try:
                default_storage.delete(user.avatar.path)
            except:
                pass
        
        # Sauvegarder le nouveau
        ext = os.path.splitext(avatar.name)[1]
        filename = f"avatars/user_{user.id}_{int(timezone.now().timestamp())}{ext}"
        filepath = default_storage.save(filename, ContentFile(avatar.read()))
        
        user.avatar = filepath
        user.save()
        
        return Response({
            'avatar': user.avatar.url if user.avatar else None,
            'message': 'Avatar mis à jour avec succès'
        })


@extend_schema(
    tags=['accounts'],
    description="Statistiques de l'utilisateur connecté.",
    responses=OpenApiResponse(description="Statistiques utilisateur"),
)
class UserStatsView(APIView):
    """Statistiques de l'utilisateur"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Commandes de l'utilisateur
        orders = Order.objects.filter(user=user)
        total_orders = orders.count()
        completed_orders = orders.filter(status='PICKED_UP').count()
        
        # Calcul des repas sauvés (basé sur les commandes complétées)
        total_saved_meals = 0
        total_co2_saved = 0
        for order in orders.filter(status='PICKED_UP'):
            total_saved_meals += order.quantity
            total_co2_saved += order.quantity * 2.5
        
        # Points (basés sur les repas sauvés)
        total_points = total_saved_meals * 10
        
        # Badges
        badges = []
        if total_saved_meals >= 1:
            badges.append({
                'id': '1',
                'name': 'Premier Sauvetage',
                'description': 'Premier repas sauvé',
                'earned_at': timezone.now().isoformat()
            })
        if total_saved_meals >= 10:
            badges.append({
                'id': '2',
                'name': 'Eco Saver',
                'description': '10 repas sauvés',
                'earned_at': timezone.now().isoformat()
            })
        if total_saved_meals >= 50:
            badges.append({
                'id': '3',
                'name': 'Top Fan',
                'description': '50 repas sauvés',
                'earned_at': timezone.now().isoformat()
            })
        
        # Prochain badge - CORRECTION ICI
        next_badge = 'Eco Champion'
        points_needed_for_next = 200
        current_progress = total_points % points_needed_for_next
        points_to_next = points_needed_for_next - current_progress
        
        return Response({
            'total_orders': total_orders,
            'total_saved_meals': total_saved_meals,
            'total_co2_saved': round(total_co2_saved, 1),
            'total_points': total_points,
            'next_badge': next_badge,
            'points_to_next_badge': points_to_next,
            'badges': badges
        })

@extend_schema(
    tags=['accounts'],
    description="Récupérer et mettre à jour les paramètres utilisateur.",
    responses=OpenApiResponse(description="Paramètres utilisateur"),
)
class UserSettingsView(APIView):
    """Récupérer et mettre à jour les paramètres utilisateur"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'favorite_address': getattr(user, 'favorite_address', 'Non renseigné'),
            'notifications_enabled': getattr(user, 'notifications_enabled', True),
            'language': getattr(user, 'language', 'Français')
        })

    def post(self, request):
        user = request.user
        
        if 'favorite_address' in request.data:
            user.favorite_address = request.data['favorite_address']
        if 'notifications_enabled' in request.data:
            user.notifications_enabled = request.data['notifications_enabled']
        if 'language' in request.data:
            user.language = request.data['language']
        
        user.save()
        
        return Response({
            'favorite_address': getattr(user, 'favorite_address', 'Non renseigné'),
            'notifications_enabled': getattr(user, 'notifications_enabled', True),
            'language': getattr(user, 'language', 'Français'),
            'message': 'Paramètres mis à jour'
        })