from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.is_admin


class CanScan(BasePermission):
    """Invigilators and admins can scan."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.can_scan)
