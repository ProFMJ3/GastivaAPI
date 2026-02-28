from rest_framework import permissions


class IsPartnerOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission: public read, write only for owner.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class IsPartnerOwnerOrAdmin(permissions.BasePermission):
    """
    Permission: owner or admin can modify.
    """
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user or request.user.role == 'ADMIN'


class CanCreatePartner(permissions.BasePermission):
    """
    Permission: only users with PARTNER role can create.
    """
    def has_permission(self, request, view):
        if request.method == 'POST':
            return request.user.is_authenticated and request.user.role == 'PARTNER'
        return True


class IsAdminForStatusUpdate(permissions.BasePermission):
    """
    Permission: only admins can change status.
    """
    def has_object_permission(self, request, view, obj):
        if 'status' in request.data and request.data['status'] != obj.status:
            return request.user.role == 'ADMIN'
        return True


class IsMyPartner(permissions.BasePermission):
    """
    Permission: check if the partner belongs to the user.
    """
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user