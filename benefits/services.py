from __future__ import annotations

import datetime
from typing import Any
from django.db import transaction
from django.utils import timezone
from common.exceptions import BusinessRuleViolationError, PermissionDeniedError, ValidationError
from accounts.rbac import PERM_GRANT_BENEFITS, PERM_MANAGE_BENEFITS, has_unit_permission
from beneficiaries.models import Family, FamilyMember
from benefits.exceptions import (
    BenefitAlreadyGrantedError,
    BenefitEditNotAllowedError,
    BenefitInactiveError,
    BenefitInheritanceError,
    BenefitProtectedError,
    BenefitScopeMismatchError,
)
from benefits.models import Benefit, BenefitGrant, BenefitPeriod, BenefitScope, BenefitType, get_current_year
from organizational.models import OrganizationalUnit


@transaction.atomic
def benefit_create(
    *,
    name: str,
    unit: OrganizationalUnit,
    year: int | None = None,
    benefit_type: str = BenefitType.CESTA_BASICA,
    period: str = BenefitPeriod.UNICO,
    scope: str = BenefitScope.FAMILIAR,
    is_active: bool = True,
    description: str = "",
    quantity_available: int | None = None,
    actor_user: Any | None = None,
) -> Benefit:
    """
    Creates a new social benefit originating in a specific organizational unit.
    """
    if actor_user and not has_unit_permission(actor_user, unit, PERM_MANAGE_BENEFITS):
        raise PermissionDeniedError(
            f"Usuário '{actor_user}' não possui permissão para criar benefícios na unidade '{unit.name}'."
        )

    name = name.strip()
    if not name:
        raise ValidationError("O nome do benefício é obrigatório.")

    if benefit_type not in BenefitType.values:
        raise ValidationError(f"Tipo de benefício '{benefit_type}' inválido.")

    if period not in BenefitPeriod.values:
        raise ValidationError(f"Periodicidade '{period}' inválida.")

    if scope not in BenefitScope.values:
        raise ValidationError(f"Escopo '{scope}' inválido.")

    benefit = Benefit(
        name=name,
        unit=unit,
        year=year or get_current_year(),
        benefit_type=benefit_type,
        period=period,
        scope=scope,
        is_active=is_active,
        description=description.strip(),
        quantity_available=quantity_available,
    )
    benefit.full_clean()
    benefit.save()
    return benefit


@transaction.atomic
def benefit_update(
    benefit: Benefit,
    *,
    name: str | None = None,
    year: int | None = None,
    benefit_type: str | None = None,
    period: str | None = None,
    scope: str | None = None,
    is_active: bool | None = None,
    description: str | None = None,
    quantity_available: int | None | object = ...,
    actor_user: Any | None = None,
    actor_unit: OrganizationalUnit | None = None,
) -> Benefit:
    """
    Updates an existing benefit.
    Rule: Child units cannot edit inherited benefits created by ancestor units.
    """
    if actor_unit and actor_unit.pk != benefit.unit_id:
        raise BenefitEditNotAllowedError(
            f"A unidade '{actor_unit.name}' não pode editar o benefício '{benefit.name}', "
            f"pois ele foi criado pela unidade superior '{benefit.unit.name}'."
        )

    if actor_user and not has_unit_permission(actor_user, benefit.unit, PERM_MANAGE_BENEFITS):
        raise PermissionDeniedError(
            f"Usuário '{actor_user}' não possui permissão para editar benefícios na unidade '{benefit.unit.name}'."
        )

    if name is not None:
        n = name.strip()
        if not n:
            raise ValidationError("O nome do benefício não pode ficar em branco.")
        benefit.name = n

    if year is not None:
        benefit.year = year

    if benefit_type is not None:
        if benefit_type not in BenefitType.values:
            raise ValidationError(f"Tipo de benefício '{benefit_type}' inválido.")
        benefit.benefit_type = benefit_type

    if period is not None:
        if period not in BenefitPeriod.values:
            raise ValidationError(f"Periodicidade '{period}' inválida.")
        benefit.period = period

    if scope is not None:
        if scope not in BenefitScope.values:
            raise ValidationError(f"Escopo '{scope}' inválido.")
        # If scope is changing, ensure no existing grants conflict
        if benefit.grants.exists() and scope != benefit.scope:
            raise BusinessRuleViolationError(
                "Não é permitido alterar o escopo de um benefício que já possui concessões registradas."
            )
        benefit.scope = scope

    if is_active is not None:
        benefit.is_active = is_active

    if description is not None:
        benefit.description = description.strip()

    if quantity_available is not ...:
        benefit.quantity_available = quantity_available  # type: ignore

    benefit.full_clean()
    benefit.save()
    return benefit


@transaction.atomic
def benefit_delete(
    benefit: Benefit,
    *,
    actor_user: Any | None = None,
) -> None:
    """
    Deletes a benefit.
    Rule: Benefits with historical grants cannot be deleted.
    """
    if actor_user and not has_unit_permission(actor_user, benefit.unit, PERM_MANAGE_BENEFITS):
        raise PermissionDeniedError(
            f"Usuário '{actor_user}' não possui permissão para excluir benefícios na unidade '{benefit.unit.name}'."
        )

    if benefit.grants.exists():
        raise BenefitProtectedError(
            f"O benefício '{benefit.name}' não pode ser excluído porque possui concessões históricas vinculadas."
        )

    benefit.delete()


@transaction.atomic
def benefit_grant_create(
    *,
    benefit: Benefit,
    family: Family,
    grant_unit: OrganizationalUnit,
    member: FamilyMember | None = None,
    granted_by: Any | None = None,
    granted_at: datetime.datetime | None = None,
    quantity: int = 1,
    notes: str = "",
    actor_user: Any | None = None,
) -> BenefitGrant:
    """
    Registers a benefit concession for a family or an individual family member.

    Validations & Business Rules:
    1. Actor must have GRANT_BENEFITS permission on grant_unit.
    2. Benefit must be active (is_active=True).
    3. Grant unit must be the benefit's unit or a descendant of it (Benefit Inheritance).
    4. Family must be linked to the grant_unit or in its accessible hierarchy.
    5. If scope is FAMILIAR: member must be None, and cannot be granted more than once to this family.
    6. If scope is INDIVIDUAL: member must be provided and belong to the family.
    7. Quantity must be positive and not exceed quantity_available (if set).
    """
    user_to_check = actor_user or granted_by
    if user_to_check and not has_unit_permission(user_to_check, grant_unit, PERM_GRANT_BENEFITS):
        raise PermissionDeniedError(
            f"Usuário não tem permissão para conceder benefícios na unidade '{grant_unit.name}'."
        )

    if not benefit.is_active:
        raise BenefitInactiveError(
            f"O benefício '{benefit.name}' está inativo e não pode receber novas concessões."
        )

    # Benefit inheritance validation: grant_unit must be benefit.unit or a descendant of benefit.unit
    allowed_grant_unit_ids = benefit.unit.get_descendant_ids(include_self=True)
    if grant_unit.pk not in allowed_grant_unit_ids:
        raise BenefitInheritanceError(
            f"A unidade '{grant_unit.name}' não tem acesso ao benefício '{benefit.name}', "
            f"pois não pertence à hierarquia da unidade criadora '{benefit.unit.name}'."
        )

    # Validate family belongs to grant_unit hierarchy
    if family.unit_id != grant_unit.pk and family.unit_id not in grant_unit.get_descendant_ids(include_self=True):
        if grant_unit.pk not in family.unit.get_ancestor_ids(include_self=True):
            raise ValidationError(
                f"A família '{family.representative_name}' (unidade: {family.unit.name}) "
                f"não pode receber benefícios da unidade '{grant_unit.name}'."
            )

    if quantity < 1:
        raise ValidationError("A quantidade concedida deve ser de pelo menos 1.")

    # Scope validation
    if benefit.scope == BenefitScope.FAMILIAR:
        if member is not None:
            raise BenefitScopeMismatchError(
                f"O benefício '{benefit.name}' possui escopo familiar e não deve ser atribuído a um membro individual."
            )
        # Check if already granted to this family
        if BenefitGrant.objects.filter(benefit=benefit, family=family).exists():
            raise BenefitAlreadyGrantedError(
                f"O benefício familiar '{benefit.name}' já foi concedido anteriormente à família '{family.representative_name}'."
            )

    elif benefit.scope == BenefitScope.INDIVIDUAL:
        if member is None:
            raise BenefitScopeMismatchError(
                f"O benefício '{benefit.name}' possui escopo individual e exige a seleção de um membro da família."
            )
        if member.family_id != family.pk:
            raise ValidationError(
                f"O membro '{member.name}' não pertence à família '{family.representative_name}'."
            )

    # Quantity available stock decrement if tracked
    if benefit.quantity_available is not None:
        if benefit.quantity_available < quantity:
            raise BusinessRuleViolationError(
                f"Quantidade disponível insuficiente ({benefit.quantity_available}) para atender a solicitação ({quantity})."
            )
        benefit.quantity_available -= quantity
        benefit.save(update_fields=["quantity_available"])

    grant = BenefitGrant(
        benefit=benefit,
        family=family,
        member=member,
        grant_unit=grant_unit,
        granted_by=granted_by,
        granted_at=granted_at or timezone.now(),
        quantity=quantity,
        notes=notes.strip(),
    )
    grant.full_clean()
    grant.save()
    return grant
