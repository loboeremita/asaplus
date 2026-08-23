from __future__ import annotations

from typing import Any
from django.db import transaction
from common.exceptions import PermissionDeniedError, ValidationError
from accounts.models import RoleType, UnitMembership
from accounts.rbac import PERM_MANAGE_UNITS, has_unit_permission
from organizational.models import OrganizationalUnit


@transaction.atomic
def membership_create(
    *,
    user: Any,
    unit: OrganizationalUnit,
    role: str,
    is_active: bool = True,
    actor_user: Any | None = None,
) -> UnitMembership:
    """
    Assigns a role to a user on an organizational unit.
    """
    if actor_user and not has_unit_permission(actor_user, unit, PERM_MANAGE_UNITS):
        raise PermissionDeniedError(
            f"Usuário '{actor_user}' não tem permissão para gerenciar membros na unidade '{unit.name}'."
        )

    if role not in RoleType.values:
        raise ValidationError(f"Papel '{role}' inválido.")

    membership, created = UnitMembership.objects.update_or_create(
        user=user,
        unit=unit,
        defaults={"role": role, "is_active": is_active},
    )
    return membership


@transaction.atomic
def membership_update(
    membership: UnitMembership,
    *,
    role: str | None = None,
    is_active: bool | None = None,
    actor_user: Any | None = None,
) -> UnitMembership:
    """
    Updates an existing unit membership.
    """
    if actor_user and not has_unit_permission(actor_user, membership.unit, PERM_MANAGE_UNITS):
        raise PermissionDeniedError(
            f"Usuário '{actor_user}' não tem permissão para gerenciar membros na unidade '{membership.unit.name}'."
        )

    if role is not None:
        if role not in RoleType.values:
            raise ValidationError(f"Papel '{role}' inválido.")
        membership.role = role

    if is_active is not None:
        membership.is_active = is_active

    membership.full_clean()
    membership.save()
    return membership


@transaction.atomic
def membership_delete(
    membership: UnitMembership,
    *,
    actor_user: Any | None = None,
) -> None:
    """
    Removes a unit membership.
    """
    if actor_user and not has_unit_permission(actor_user, membership.unit, PERM_MANAGE_UNITS):
        raise PermissionDeniedError(
            f"Usuário '{actor_user}' não tem permissão para remover membros na unidade '{membership.unit.name}'."
        )

    membership.delete()
