from rest_framework import permissions

from parkings.models import DataUser


class IsDataUser(permissions.BasePermission):
    def has_permission(self, request, view):
        """
        Allow only data users to proceed further.
        """
        user = request.user

        if not user.is_authenticated:
            return False

        try:
            user.datauser
            return True
        except DataUser.DoesNotExist:
            pass

        return False
