from __future__ import annotations

from django.db.models import QuerySet
from beneficiaries.models import Family, FamilyMember
from benefits.models import Benefit, BenefitGrant
from organizational.models import OrganizationalUnit


def benefit_get_by_id(benefit_id: int) -> Benefit | None:
    """Retrieve a benefit by its ID."""
    try:
        return Benefit.objects.select_related("unit").get(pk=benefit_id)
    except Benefit.DoesNotExist:
        return None


def benefit_get_available_for_unit(
    unit: OrganizationalUnit,
    active_only: bool = True,
) -> QuerySet[Benefit]:
    """
    Retrieves all benefits available to a unit:
    includes benefits created by the unit itself plus all benefits created by ancestor units.
    """
    ancestor_ids = unit.get_ancestor_ids(include_self=True)
    qs = Benefit.objects.filter(unit_id__in=ancestor_ids).select_related("unit")
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def benefit_list_created_by_unit(
    unit: OrganizationalUnit,
    active_only: bool = True,
) -> QuerySet[Benefit]:
    """Retrieves benefits created directly by the specified unit."""
    qs = Benefit.objects.filter(unit=unit).select_related("unit")
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def benefit_get_grants_for_family(family: Family) -> QuerySet[BenefitGrant]:
    """Retrieves all grants issued to a family (including its individual members)."""
    return (
        BenefitGrant.objects.filter(family=family)
        .select_related("benefit", "member", "grant_unit", "granted_by")
        .order_by("-granted_at")
    )


def benefit_get_grants_for_member(member: FamilyMember) -> QuerySet[BenefitGrant]:
    """Retrieves all individual grants issued to a specific member."""
    return (
        BenefitGrant.objects.filter(member=member)
        .select_related("benefit", "family", "grant_unit", "granted_by")
        .order_by("-granted_at")
    )


def benefit_get_grants_by_unit(
    unit: OrganizationalUnit,
    include_descendants: bool = False,
) -> QuerySet[BenefitGrant]:
    """Retrieves all grants executed by a unit (or throughout descendant units)."""
    if include_descendants:
        unit_ids = unit.get_descendant_ids(include_self=True)
        qs = BenefitGrant.objects.filter(grant_unit_id__in=unit_ids)
    else:
        qs = BenefitGrant.objects.filter(grant_unit=unit)

    return qs.select_related("benefit", "family", "member", "grant_unit", "granted_by").order_by("-granted_at")
