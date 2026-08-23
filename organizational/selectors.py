from __future__ import annotations

from typing import Any
from django.db.models import QuerySet
from organizational.models import OrganizationalUnit


def unit_get_by_id(unit_id: int) -> OrganizationalUnit | None:
    """Retrieve an organizational unit by its ID."""
    try:
        return OrganizationalUnit.objects.select_related("parent").get(pk=unit_id)
    except OrganizationalUnit.DoesNotExist:
        return None


def unit_list_active() -> QuerySet[OrganizationalUnit]:
    """Retrieve all active organizational units."""
    return OrganizationalUnit.objects.filter(is_active=True).select_related("parent")


def unit_get_descendants(
    unit: OrganizationalUnit,
    include_self: bool = True,
    active_only: bool = False,
) -> QuerySet[OrganizationalUnit]:
    """Retrieve all descendants of a unit as a QuerySet."""
    descendant_ids = unit.get_descendant_ids(include_self=include_self)
    qs = OrganizationalUnit.objects.filter(id__in=descendant_ids).select_related("parent")
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def unit_get_descendant_ids(unit: OrganizationalUnit, include_self: bool = True) -> set[int]:
    """Retrieve all descendant IDs of a unit."""
    return unit.get_descendant_ids(include_self=include_self)


def unit_get_ancestors(unit: OrganizationalUnit, include_self: bool = True) -> list[OrganizationalUnit]:
    """Retrieve all ancestor units ordered from closest to root."""
    return unit.get_ancestors(include_self=include_self)


def unit_get_ancestor_ids(unit: OrganizationalUnit, include_self: bool = True) -> set[int]:
    """Retrieve all ancestor IDs of a unit."""
    return unit.get_ancestor_ids(include_self=include_self)


def unit_get_tree(root_unit: OrganizationalUnit | None = None) -> list[dict[str, Any]]:
    """
    Build a nested hierarchical dictionary tree starting from root_unit (or all top-level roots).
    """
    if root_unit:
        all_units = unit_get_descendants(root_unit, include_self=True)
    else:
        all_units = OrganizationalUnit.objects.all()

    units_by_parent: dict[int | None, list[OrganizationalUnit]] = {}
    for unit in all_units:
        p_id = unit.parent_id
        units_by_parent.setdefault(p_id, []).append(unit)

    def _build_nodes(parent_id: int | None) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for child in units_by_parent.get(parent_id, []):
            nodes.append({
                "id": child.id,
                "name": child.name,
                "code": child.code,
                "unit_type": child.unit_type,
                "unit_type_display": child.get_unit_type_display(),
                "is_active": child.is_active,
                "children": _build_nodes(child.id),
            })
        return nodes

    root_parent_id = root_unit.parent_id if root_unit else None
    return _build_nodes(root_parent_id)
