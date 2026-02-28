from rest_framework import permissions


class IsOfferOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission: public read, write only for partner owner.
    """
    def has_object_permission(self, request, view, obj):
        # Read allowed for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write reserved for partner owner
        return request.user.is_authenticated and obj.partner.owner == request.user


class CanCreateOffer(permissions.BasePermission):
    """
    Permission: only partners with at least one partner can create offers.
    """
    def has_permission(self, request, view):
        if request.method == 'POST':
            if not request.user.is_authenticated:
                return False
            if request.user.role != 'PARTNER':
                return False
            # Check if user has at least one partner
            return request.user.partners.exists()
        return True


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission: owner or admin can modify/delete.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user.is_authenticated and
            (obj.partner.owner == request.user or request.user.role == 'ADMIN')
        )


class CanManageOffer(permissions.BasePermission):
    """
    Permission: check if user can manage offers for a specific partner.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # For create, check if user has the partner
        if request.method == 'POST' and 'partner_id' in request.data:
            partner_id = request.data.get('partner_id')
            return request.user.partners.filter(id=partner_id).exists()
        
        return True