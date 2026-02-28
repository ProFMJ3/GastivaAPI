from rest_framework import permissions


class IsPaymentOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission : le client propriétaire peut voir son paiement.
    """
    def has_object_permission(self, request, view, obj):
        # Lecture autorisée pour le client et le restaurant
        if request.method in permissions.SAFE_METHODS:
            return (obj.order.client == request.user or 
                    obj.order.restaurant.owner == request.user or
                    request.user.role == 'ADMIN')
        
        # Écriture réservée
        return request.user.role == 'ADMIN'


class CanCreatePayment(permissions.BasePermission):
    """
    Permission : seulement le client peut créer un paiement pour sa commande.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'CLIENT'


class CanProcessPayment(permissions.BasePermission):
    """
    Permission : seulement le client peut traiter son paiement.
    """
    def has_object_permission(self, request, view, obj):
        return obj.order.client == request.user or request.user.role == 'ADMIN'