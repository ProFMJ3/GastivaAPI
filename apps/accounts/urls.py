from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentification
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profil
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/update/', views.UserProfileUpdateView.as_view(), name='profile-update'),
    path('profile/avatar/', views.AvatarUploadView.as_view(), name='avatar-upload'),
    path('profile/stats/', views.UserStatsView.as_view(), name='user-stats'),
    path('profile/settings/', views.UserSettingsView.as_view(), name='user-settings'),
]