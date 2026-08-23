from __future__ import annotations

from typing import Any
from django.db.models import QuerySet
from accounts.models import UnitMembership
from organizational.models import OrganizationalUnit


def membership_list_by_user(user: Any, active_only: bool = True) -> QuerySet[UnitMembership]:
    """Retrieve all memberships for a user."""
    qs = UnitMembership.objects.filter(user=user).select_related("unit", "user")
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def membership_list_by_unit(
    unit: OrganizationalUnit,
    active_only: bool = True,
    include_descendants: bool = False,
) -> QuerySet[UnitMembership]:
    """Retrieve memberships for a unit (optionally including descendant units)."""
    if include_descendants:
        unit_ids = unit.get_descendant_ids(include_self=True)
        qs = UnitMembership.objects.filter(unit_id__in=unit_ids)
    else:
        qs = UnitMembership.objects.filter(unit=unit)

    qs = qs.select_related("unit", "user")
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def membership_get(user: Any, unit: OrganizationalUnit) -> UnitMembership | None:
    """Retrieve the direct membership for a user on a unit."""
    try:
        return UnitMembership.objects.select_related("unit", "user").get(user=user, unit=unit)
    except UnitMembership.DoesNotExist:
        return None
