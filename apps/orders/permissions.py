from rest_framework import permissions


class IsOrderClientOrReadOnly(permissions.BasePermission):
    """
    Permission : le client propriétaire peut voir/modifier sa commande.
    """
    def has_object_permission(self, request, view, obj):
        # Lecture autorisée pour le client et le partner
        if request.method in permissions.SAFE_METHODS:
            return obj.client == request.user or obj.partner.owner == request.user
        
        # Écriture réservée au client propriétaire
        return obj.client == request.user


class IsOrderPartnerOrClient(permissions.BasePermission):
    """
    Permission : le partner peut modifier le statut, le client peut annuler.
    """
    def has_object_permission(self, request, view, obj):
        # Le partner peut tout faire sur ses commandes
        if request.user == obj.partner.owner:
            return True
        
        # Le client peut seulement annuler les commandes en attente
        if request.user == obj.client and obj.status in ['PENDING']:
            return request.method in ['PATCH', 'DELETE']
        
        return False


class CanCreateOrder(permissions.BasePermission):
    """
    Permission : seulement les clients peuvent créer des commandes.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'CLIENT'