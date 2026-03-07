from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # ========================================================================
    # LISTES ET STATISTIQUES
    # ========================================================================
    
    # GET /api/notifications/ - Liste des notifications
    path('',
         views.NotificationListView.as_view(),
         name='notification-list'),
    
    # GET /api/notifications/stats/ - Statistiques
    path('stats/',
         views.NotificationStatsView.as_view(),
         name='notification-stats'),
    
    # GET /api/notifications/unread-count/ - Compteur non lues
    path('unread-count/',
         views.NotificationUnreadCountView.as_view(),
         name='notification-unread-count'),
    
    # ========================================================================
    # PRÉFÉRENCES
    # ========================================================================
    
    # GET/PUT /api/notifications/preferences/ - Préférences
    path('preferences/',
         views.NotificationPreferenceView.as_view(),
         name='notification-preferences'),
    
    # ========================================================================
    # ACTIONS SUR LES NOTIFICATIONS
    # ========================================================================
    
    # POST /api/notifications/mark-read/ - Marquer comme lues
    path('mark-read/',
         views.NotificationMarkReadView.as_view(),
         name='notification-mark-read'),
    
    # POST /api/notifications/mark-all-read/ - Marquer toutes comme lues
    path('mark-all-read/',
         views.NotificationMarkAllReadView.as_view(),
         name='notification-mark-all-read'),
    
    # DELETE /api/notifications/delete-all/ - Supprimer toutes
    path('delete-all/',
         views.NotificationDeleteAllView.as_view(),
         name='notification-delete-all'),
    
    # ========================================================================
    # CRUD NOTIFICATIONS (Admin)
    # ========================================================================
    
    # POST /api/notifications/create/ - Créer une notification (admin)
    path('create/',
         views.NotificationCreateView.as_view(),
         name='notification-create'),
    
    # GET /api/notifications/<int:pk>/ - Détails d'une notification
    path('<int:pk>/',
         views.NotificationDetailView.as_view(),
         name='notification-detail'),
    
    # DELETE /api/notifications/<int:pk>/delete/ - Supprimer une notification
    path('<int:pk>/delete/',
         views.NotificationDeleteView.as_view(),
         name='notification-delete'),
]