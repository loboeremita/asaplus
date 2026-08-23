from __future__ import annotations

from typing import Any
from django.db.models import QuerySet
from beneficiaries.models import Family, FamilyMember
from organizational.models import OrganizationalUnit


def family_get_by_id(family_id: int) -> Family | None:
    """Retrieves a family by its ID, prefetching members and unit."""
    try:
        return (
            Family.objects.select_related("unit")
            .prefetch_related("members")
            .get(pk=family_id)
        )
    except Family.DoesNotExist:
        return None


def family_list_by_unit(
    unit: OrganizationalUnit,
    include_descendants: bool = False,
    active_only: bool = True,
) -> QuerySet[Family]:
    """Retrieves families registered in a unit (or throughout descendant units)."""
    if include_descendants:
        unit_ids = unit.get_descendant_ids(include_self=True)
        qs = Family.objects.filter(unit_id__in=unit_ids)
    else:
        qs = Family.objects.filter(unit=unit)

    qs = qs.select_related("unit").prefetch_related("members")
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def family_get_members(family: Family) -> QuerySet[FamilyMember]:
    """Retrieves all members belonging to a family."""
    return family.members.all()


def family_get_aggregated_benefits(family_or_id: Family | int) -> dict[str, Any]:
    """
    Returns an aggregated overview of all benefits granted to the family
    (both family-scoped and individual member-scoped concessions).
    """
    if isinstance(family_or_id, Family):
        family = family_or_id
    else:
        family = family_get_by_id(family_or_id)  # type: ignore
        if not family:
            return {}

    # Import dynamically to avoid circular import issues
    from benefits.models import BenefitGrant

    grants = (
        BenefitGrant.objects.filter(family=family)
        .select_related("benefit", "member", "grant_unit", "granted_by")
        .order_by("-granted_at")
    )

    timeline: list[dict[str, Any]] = []
    distinct_benefits_ids: set[int] = set()
    total_quantity: int = 0

    for grant in grants:
        distinct_benefits_ids.add(grant.benefit_id)
        total_quantity += grant.quantity

        recipient_name = (
            f"Membro: {grant.member.name} ({grant.member.get_kinship_display()})"
            if grant.member
            else f"Família: {family.representative_name}"
        )

        timeline.append({
            "grant_id": grant.id,
            "benefit_id": grant.benefit_id,
            "benefit_name": grant.benefit.name,
            "benefit_type": grant.benefit.benefit_type,
            "benefit_type_display": grant.benefit.get_benefit_type_display(),
            "scope": grant.benefit.scope,
            "scope_display": grant.benefit.get_scope_display(),
            "recipient_name": recipient_name,
            "member_id": grant.member_id,
            "quantity": grant.quantity,
            "granted_at": grant.granted_at,
            "grant_unit_name": grant.grant_unit.name,
            "granted_by_username": grant.granted_by.username if grant.granted_by else None,
            "notes": grant.notes,
        })

    last_grant_date = timeline[0]["granted_at"] if timeline else None

    return {
        "family_id": family.id,
        "representative_name": family.representative_name,
        "unit_name": family.unit.name,
        "total_grants_count": len(timeline),
        "total_items_quantity": total_quantity,
        "distinct_benefits_count": len(distinct_benefits_ids),
        "last_grant_date": last_grant_date,
        "grants": timeline,
    }
