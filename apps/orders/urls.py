from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # ========================================================================
    # LISTES DE COMMANDES
    # ========================================================================
    # GET /api/orders/ - Liste des commandes
    path('',
         views.OrderListView.as_view(),
         name='order-list'),
    
    # GET /api/orders/active/ - Commandes en cours
    path('active/',
         views.OrderActiveListView.as_view(),
         name='order-active'),
    
    # GET /api/orders/history/ - Historique des commandes
    path('history/',
         views.OrderHistoryListView.as_view(),
         name='order-history'),
    
    # GET /api/orders/stats/ - Statistiques
    path('stats/',
         views.OrderStatsView.as_view(),
         name='order-stats'),
    
    # ========================================================================
    # CRUD COMMANDES
    # ========================================================================
    # POST /api/orders/create/ - Créer une commande
    path('create/',
         views.OrderCreateView.as_view(),
         name='order-create'),
    
    # GET /api/orders/<int:pk>/ - Détails d'une commande
    path('<int:pk>/',
         views.OrderDetailView.as_view(),
         name='order-detail'),
    
    # ========================================================================
    # ACTIONS SUR LES COMMANDES
    # ========================================================================
    # PATCH /api/orders/<int:pk>/status/ - Mettre à jour le statut
    path('<int:pk>/status/',
         views.OrderStatusUpdateView.as_view(),
         name='order-status'),
    
    # POST /api/orders/<int:pk>/cancel/ - Annuler
    path('<int:pk>/cancel/',
         views.OrderCancelView.as_view(),
         name='order-cancel'),
    
    # POST /api/orders/<int:pk>/confirm/ - Confirmer (restaurant)
    path('<int:pk>/confirm/',
         views.OrderConfirmView.as_view(),
         name='order-confirm'),
    
    # POST /api/orders/<int:pk>/ready/ - Prêt (restaurant)
    path('<int:pk>/ready/',
         views.OrderReadyView.as_view(),
         name='order-ready'),
    
    # POST /api/orders/<int:pk>/pickup/ - Retiré (client/restaurant)
    path('<int:pk>/pickup/',
         views.OrderPickupView.as_view(),
         name='order-pickup'),
]