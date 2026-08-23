from __future__ import annotations

from functools import wraps
from typing import Any, Callable
from django.contrib.auth.models import AnonymousUser
from django.db.models import QuerySet
from common.exceptions import PermissionDeniedError
from accounts.models import RoleType, UnitMembership
from organizational.models import OrganizationalUnit

# Permission Identifiers
PERM_MANAGE_UNITS = "manage_units"
PERM_MANAGE_BENEFITS = "manage_benefits"
PERM_REGISTER_BENEFICIARIES = "register_beneficiaries"
PERM_GRANT_BENEFITS = "grant_benefits"
PERM_VIEW_DATA = "view_data"

# Role-to-Permissions Matrix
ROLE_PERMISSIONS: dict[str, set[str]] = {
    RoleType.ADMIN: {
        PERM_MANAGE_UNITS,
        PERM_MANAGE_BENEFITS,
        PERM_REGISTER_BENEFICIARIES,
        PERM_GRANT_BENEFITS,
        PERM_VIEW_DATA,
    },
    RoleType.PASTOR: {
        PERM_MANAGE_BENEFITS,
        PERM_REGISTER_BENEFICIARIES,
        PERM_GRANT_BENEFITS,
        PERM_VIEW_DATA,
    },
    RoleType.DIRECTOR: {
        PERM_MANAGE_BENEFITS,
        PERM_REGISTER_BENEFICIARIES,
        PERM_GRANT_BENEFITS,
        PERM_VIEW_DATA,
    },
    RoleType.SECRETARY: {
        PERM_VIEW_DATA,
    },
    RoleType.ASSISTANT: {
        PERM_REGISTER_BENEFICIARIES,
        PERM_GRANT_BENEFITS,
        PERM_VIEW_DATA,
    },
}


def get_role_permissions(role: str) -> set[str]:
    """Returns the set of permissions associated with a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def get_user_effective_roles_for_unit(user: Any, unit: OrganizationalUnit) -> set[str]:
    """
    Returns all effective roles the user holds for the target unit,
    taking into account direct assignment and hierarchical inheritance from ancestor units.
    """
    if not user or isinstance(user, AnonymousUser) or not user.is_authenticated or not user.is_active:
        return set()

    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return {RoleType.ADMIN}

    ancestor_ids = unit.get_ancestor_ids(include_self=True)
    roles = set(
        UnitMembership.objects.filter(
            user=user,
            unit_id__in=ancestor_ids,
            is_active=True,
        ).values_list("role", flat=True)
    )
    return roles


def has_unit_permission(user: Any, unit: OrganizationalUnit, permission_code: str) -> bool:
    """
    Checks if a user has a specific permission on an organizational unit
    (or any of its ancestor units through inheritance).
    """
    if not user or isinstance(user, AnonymousUser) or not user.is_authenticated or not user.is_active:
        return False

    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True

    effective_roles = get_user_effective_roles_for_unit(user, unit)
    for role in effective_roles:
        if permission_code in get_role_permissions(role):
            return True

    return False


def check_user_unit_permission(user: Any, unit: OrganizationalUnit, permission_code: str) -> None:
    """
    Raises PermissionDeniedError if the user does not possess the required permission.
    """
    if not has_unit_permission(user, unit, permission_code):
        raise PermissionDeniedError(
            f"Usuário não possui a permissão '{permission_code}' na unidade '{unit.name}'."
        )


def get_user_accessible_units(
    user: Any,
    permission_code: str | None = None,
) -> QuerySet[OrganizationalUnit]:
    """
    Returns a QuerySet of all units that the user can access
    (optionally requiring a specific permission_code).
    """
    if not user or isinstance(user, AnonymousUser) or not user.is_authenticated or not user.is_active:
        return OrganizationalUnit.objects.none()

    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return OrganizationalUnit.objects.filter(is_active=True)

    memberships = UnitMembership.objects.filter(user=user, is_active=True).select_related("unit")

    accessible_unit_ids: set[int] = set()
    for membership in memberships:
        if permission_code is None or permission_code in get_role_permissions(membership.role):
            descendant_ids = membership.unit.get_descendant_ids(include_self=True)
            accessible_unit_ids.update(descendant_ids)

    return OrganizationalUnit.objects.filter(id__in=accessible_unit_ids, is_active=True)


def require_unit_permission(permission_code: str, unit_kwarg: str = "unit_id"):
    """
    View decorator to enforce unit-level RBAC permission.
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped_view(request: Any, *args: Any, **kwargs: Any):
            unit_id = kwargs.get(unit_kwarg)
            if not unit_id:
                raise PermissionDeniedError("Identificador da unidade não encontrado na requisição.")

            try:
                unit = OrganizationalUnit.objects.get(pk=unit_id)
            except OrganizationalUnit.DoesNotExist:
                raise PermissionDeniedError("Unidade organizacional não encontrada.")

            check_user_unit_permission(request.user, unit, permission_code)
            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator
