from rest_framework.permissions import BasePermission


class IsSiteOwner(BasePermission):
    """
    Allows access only to users with the 'SITE_OWNER' role.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'SITE_OWNER')


class IsClinicOwner(BasePermission):
    """
    Allows access only to users with the 'CLINIC_OWNER' role.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'CLINIC_OWNER')


class IsDoctor(BasePermission):
    """
    Allows access only to users with the 'DOCTOR' role.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'DOCTOR')


class IsReception(BasePermission):
    """
    Allows access only to users with the 'RECEPTION' role.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'RECEPTION')