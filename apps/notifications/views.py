from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from .models import Notification, NotificationPreference
from .serializers import (
    NotificationSerializer, NotificationDetailSerializer,
    NotificationCreateSerializer, NotificationMarkReadSerializer,
    NotificationPreferenceSerializer, NotificationStatsSerializer
)
from apps.accounts.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin


@extend_schema(
    tags=['notifications'],
    summary="Liste des notifications",
    description="Retourne la liste des notifications de l'utilisateur connecté.",
    parameters=[
        OpenApiParameter(name='is_read', description='Filtrer par statut de lecture', required=False, type=bool),
        OpenApiParameter(name='notification_type', description='Filtrer par type', required=False, type=str),
        OpenApiParameter(name='priority', description='Filtrer par priorité', required=False, type=str),
        OpenApiParameter(name='from_date', description='Date de début', required=False, type=str),
        OpenApiParameter(name='to_date', description='Date de fin', required=False, type=str),
    ],
)
class NotificationListView(generics.ListAPIView):
    """
    Liste des notifications de l'utilisateur connecté.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Pour Swagger, retourner un queryset vide sans vérification d'utilisateur
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        
        user = self.request.user
        queryset = Notification.objects.filter(recipient=user)

        # Filtres
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            queryset = queryset.filter(is_read=is_read_bool)

        notification_type = self.request.query_params.get('notification_type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        from_date = self.request.query_params.get('from_date')
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)

        to_date = self.request.query_params.get('to_date')
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)

        # Exclure les notifications expirées
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )

        return queryset.order_by('-created_at')


@extend_schema(
    tags=['notifications'],
    summary="Détails d'une notification",
    description="Retourne les détails d'une notification spécifique.",
)
class NotificationDetailView(generics.RetrieveAPIView):
    """
    Détails d'une notification.
    """
    serializer_class = NotificationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Pour Swagger, retourner un queryset vide
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        
        # S'assurer que l'utilisateur ne voit que ses propres notifications
        return Notification.objects.filter(recipient=self.request.user)


@extend_schema(
    tags=['notifications'],
    summary="Créer une notification",
    description="Crée une nouvelle notification (admin uniquement).",
    request=NotificationCreateSerializer,
    responses={
        201: NotificationSerializer,
        400: "Données invalides",
        403: "Non autorisé"
    }
)
class NotificationCreateView(generics.CreateAPIView):
    """
    Crée une nouvelle notification (admin uniquement).
    """
    serializer_class = NotificationCreateSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        notification = serializer.save()
        # Ici, vous pourriez déclencher l'envoi de notifications push/email/sms


@extend_schema(
    tags=['notifications'],
    summary="Marquer comme lue",
    description="Marque une ou plusieurs notifications comme lues.",
    request=NotificationMarkReadSerializer,
    responses={200: OpenApiResponse(description="Notifications marquées avec succès")}
)
class NotificationMarkReadView(APIView):
    """
    Marque les notifications comme lues.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        request=NotificationMarkReadSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = NotificationMarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        notification_ids = serializer.validated_data.get('notification_ids')
        mark_all = serializer.validated_data.get('mark_all')

        if mark_all:
            # Marquer toutes les notifications non lues
            notifications = Notification.objects.filter(
                recipient=user,
                is_read=False
            )
            count = notifications.count()
            notifications.update(is_read=True, read_at=timezone.now())
            message = f"{count} notification(s) marquée(s) comme lue(s)."
        elif notification_ids:
            # Marquer des notifications spécifiques
            notifications = Notification.objects.filter(
                id__in=notification_ids,
                recipient=user
            )
            count = notifications.count()
            notifications.update(is_read=True, read_at=timezone.now())
            message = f"{count} notification(s) marquée(s) comme lue(s)."
        else:
            return Response(
                {"detail": "Veuillez spécifier des IDs ou marquer toutes."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "success": True,
            "message": message,
            "count": count
        })


@extend_schema(
    tags=['notifications'],
    summary="Marquer toutes comme lues",
    description="Marque toutes les notifications de l'utilisateur comme lues.",
    responses={200: dict}
)
class NotificationMarkAllReadView(APIView):
    """
    Marque toutes les notifications comme lues.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        count = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        return Response({
            "success": True,
            "message": f"{count} notification(s) marquée(s) comme lue(s).",
            "count": count
        })


@extend_schema(
    tags=['notifications'],
    summary="Supprimer une notification",
    description="Supprime une notification.",
)
class NotificationDeleteView(generics.DestroyAPIView):
    """
    Supprime une notification.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        # Pour Swagger, retourner un queryset vide
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        
        return Notification.objects.filter(recipient=self.request.user)


@extend_schema(
    tags=['notifications'],
    summary="Supprimer toutes les notifications",
    description="Supprime toutes les notifications de l'utilisateur.",
    responses={200: dict}
)
class NotificationDeleteAllView(APIView):
    """
    Supprime toutes les notifications de l'utilisateur.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        count = Notification.objects.filter(recipient=user).delete()[0]

        return Response({
            "success": True,
            "message": f"{count} notification(s) supprimée(s).",
            "count": count
        })


@extend_schema(
    tags=['notifications'],
    summary="Préférences de notification",
    description="Récupère ou met à jour les préférences de notification de l'utilisateur.",
)
class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    """
    Gère les préférences de notification.
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj


@extend_schema(
    tags=['notifications'],
    summary="Statistiques des notifications",
    description="Retourne des statistiques sur les notifications de l'utilisateur.",
    responses={200: NotificationStatsSerializer}
)
class NotificationStatsView(APIView):
    """
    Statistiques des notifications.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        notifications = Notification.objects.filter(recipient=user)

        # Statistiques globales
        total_unread = notifications.filter(is_read=False).count()
        total_notifications = notifications.count()

        # Statistiques par type
        notifications_by_type = {}
        for notif_type, _ in Notification.NotificationType.choices:
            count = notifications.filter(notification_type=notif_type).count()
            if count > 0:
                notifications_by_type[notif_type] = count

        # Statistiques par priorité
        notifications_by_priority = {}
        for priority, _ in Notification.Priority.choices:
            count = notifications.filter(priority=priority).count()
            if count > 0:
                notifications_by_priority[priority] = count

        # Activité récente (derniers 7 jours)
        recent_activity = []
        for i in range(7):
            day = timezone.now() - timezone.timedelta(days=i)
            count = notifications.filter(
                created_at__date=day.date()
            ).count()
            recent_activity.append({
                'date': day.date().isoformat(),
                'count': count
            })

        stats = {
            'total_unread': total_unread,
            'total_notifications': total_notifications,
            'notifications_by_type': notifications_by_type,
            'notifications_by_priority': notifications_by_priority,
            'recent_activity': recent_activity
        }

        serializer = NotificationStatsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)


@extend_schema(
    tags=['notifications'],
    summary="Compteur de notifications non lues",
    description="Retourne le nombre de notifications non lues.",
    responses={200: dict}
)
class NotificationUnreadCountView(APIView):
    """
    Nombre de notifications non lues.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        count = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).count()

        return Response({
            'unread_count': count
        })