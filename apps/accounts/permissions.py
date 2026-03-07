from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée :
    - Lecture : tout le monde peut voir (GET, HEAD, OPTIONS)
    - Écriture : seulement les administrateurs peuvent modifier (POST, PUT, PATCH, DELETE)
    """
    
    def has_permission(self, request, view):
        # Les méthodes de lecture sont autorisées pour tous
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Les méthodes d'écriture nécessitent d'être admin
        return request.user and request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission personnalisée :
    - L'utilisateur peut modifier ses propres ressources
    - Les admins peuvent tout modifier
    """
    
    def has_object_permission(self, request, view, obj):
        # Les méthodes de lecture sont autorisées pour tous
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Vérifier si l'utilisateur est le propriétaire
        # Cette méthode suppose que l'objet a un attribut 'user' ou 'owner'
        if hasattr(obj, 'user'):
            return obj.user == request.user or request.user.is_staff
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user or request.user.is_staff
        elif hasattr(obj, 'client'):
            return obj.client == request.user or request.user.is_staff
        
        return request.user.is_staff


class IsPartnerOrAdmin(permissions.BasePermission):
    """
    Permission personnalisée :
    - Seuls les utilisateurs avec le rôle PARTNER ou les admins peuvent accéder
    """
    
    def has_permission(self, request, view):
        return request.user and (
            request.user.role == 'PARTNER' or 
            request.user.is_staff
        )


class IsClientOrAdmin(permissions.BasePermission):
    """
    Permission personnalisée :
    - Seuls les utilisateurs avec le rôle CLIENT ou les admins peuvent accéder
    """
    
    def has_permission(self, request, view):
        return request.user and (
            request.user.role == 'CLIENT' or 
            request.user.is_staff
        )


class IsAdminOnly(permissions.BasePermission):
    """
    Permission personnalisée :
    - Seuls les administrateurs peuvent accéder
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsOwnerOrPartnerOrAdmin(permissions.BasePermission):
    """
    Permission personnalisée :
    - Le propriétaire, le partenaire associé ou l'admin peuvent modifier
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Vérifier si l'utilisateur est le propriétaire
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Vérifier si l'utilisateur est un partenaire associé
        if hasattr(obj, 'partner') and hasattr(obj.partner, 'owner'):
            if obj.partner.owner == request.user:
                return True
        
        return request.user.is_staff


class IsVerifiedOrAdmin(permissions.BasePermission):
    """
    Permission personnalisée :
    - Les utilisateurs vérifiés ou les admins peuvent accéder
    """
    
    def has_permission(self, request, view):
        return request.user and (
            request.user.is_verified or 
            request.user.is_staff
        )


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée :
    - Lecture : tout le monde peut voir
    - Écriture : seulement le propriétaire peut modifier
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'client'):
            return obj.client == request.user
        
        return False


class IsOwnerOrPartner(permissions.BasePermission):
    """
    Permission personnalisée :
    - Le propriétaire ou le partenaire associé peuvent modifier
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Vérifier si l'utilisateur est le propriétaire
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Vérifier si l'utilisateur est un partenaire associé
        if hasattr(obj, 'partner') and hasattr(obj.partner, 'owner'):
            if obj.partner.owner == request.user:
                return True
        
        return False


class IsOwnerOrPartnerOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée :
    - Lecture : tout le monde peut voir
    - Écriture : le propriétaire ou le partenaire associé peuvent modifier
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Vérifier si l'utilisateur est le propriétaire
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Vérifier si l'utilisateur est un partenaire associé
        if hasattr(obj, 'partner') and hasattr(obj.partner, 'owner'):
            if obj.partner.owner == request.user:
                return True
        
        # Vérifier si l'utilisateur est l'owner du partner (pour les offres)
        if hasattr(obj, 'partner') and hasattr(obj.partner, 'owner'):
            if obj.partner.owner == request.user:
                return True
        
        return False