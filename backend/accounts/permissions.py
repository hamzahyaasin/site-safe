"""Role-based DRF permission classes.

Section 3.7 of the project report specifies three roles — Admin, Safety
Officer and read-only Viewer — with permissions enforced at the API layer
rather than only hidden in the interface. These classes provide that
enforcement.

The model is hierarchical rather than a set of disjoint roles: an Admin can
do anything a Safety Officer can, and a Safety Officer anything a Viewer can.
That keeps the checks to a single comparison and avoids the combinatorial
mess of per-role allow-lists on every viewset.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role


class _RoleAtLeast(BasePermission):
    """Base class: grants access when the user meets `required_role`."""

    required_role = Role.VIEWER
    message = "Your role does not permit this action."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.has_role_at_least(self.required_role)


class IsViewer(_RoleAtLeast):
    """Any authenticated user with a recognised role."""

    required_role = Role.VIEWER


class IsSafetyOfficer(_RoleAtLeast):
    """Safety Officer or Admin."""

    required_role = Role.SAFETY_OFFICER
    message = "This action requires Safety Officer privileges."


class IsAdmin(_RoleAtLeast):
    """Admin only."""

    required_role = Role.ADMIN
    message = "This action requires Admin privileges."


class ReadOnlyOrSafetyOfficer(BasePermission):
    """Everyone authenticated may read; writing requires Safety Officer.

    This is the default for operational data such as alerts and workers: a
    Viewer can monitor the dashboard but cannot resolve alerts or edit records.
    """

    message = "Viewers have read-only access; this action requires Safety Officer privileges."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return user.has_role_at_least(Role.VIEWER)
        return user.has_role_at_least(Role.SAFETY_OFFICER)


class ReadOnlyOrAdmin(BasePermission):
    """Everyone authenticated may read; writing requires Admin.

    Used for site configuration — zones, alert thresholds — which the report
    places under the Admin module.
    """

    message = "This configuration can only be changed by an Admin."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return user.has_role_at_least(Role.VIEWER)
        return user.has_role_at_least(Role.ADMIN)
