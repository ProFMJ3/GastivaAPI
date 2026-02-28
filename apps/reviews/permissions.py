from rest_framework import permissions


class IsReviewOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission : lecture publique, modification réservée au propriétaire.
    """
    def has_object_permission(self, request, view, obj):
        # Lecture autorisée pour tous si l'avis est visible
        if request.method in permissions.SAFE_METHODS:
            return obj.is_visible or request.user == obj.client or request.user.role == 'ADMIN'
        
        # Écriture réservée au propriétaire
        return request.user == obj.client


class CanCreateReview(permissions.BasePermission):
    """
    Permission : seulement les clients peuvent créer des avis.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'CLIENT'


class CanModerateReview(permissions.BasePermission):
    """
    Permission : seulement les admins peuvent modérer.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ADMIN'