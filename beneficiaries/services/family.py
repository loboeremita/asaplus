from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any
from django.db import transaction
from django.utils import timezone
from common.exceptions import PermissionDeniedError, ValidationError
from accounts.rbac import PERM_REGISTER_BENEFICIARIES, has_unit_permission
from beneficiaries.models import Family, FamilyMember, Kinship, MaritalStatus
from beneficiaries.services.viacep import ViaCEPService
from organizational.models import OrganizationalUnit


@transaction.atomic
def family_create(
    *,
    unit: OrganizationalUnit,
    representative_name: str,
    cep: str,
    number: str,
    street: str = "",
    neighborhood: str = "",
    city: str = "",
    state: str = "",
    complement: str = "",
    auto_fill_cep: bool = True,
    registration_date: datetime.date | None = None,
    monthly_income: Decimal | float | int | None = None,
    housing_status: str = "",
    notes: str = "",
    is_active: bool = True,
    actor_user: Any | None = None,
) -> Family:
    """
    Creates a new Family associated with an organizational unit.
    Optionally fetches and auto-fills address details using ViaCEP.
    """
    if actor_user and not has_unit_permission(actor_user, unit, PERM_REGISTER_BENEFICIARIES):
        raise PermissionDeniedError(
            f"Usuário '{actor_user}' não tem permissão para cadastrar famílias na unidade '{unit.name}'."
        )

    representative_name = representative_name.strip()
    if not representative_name:
        raise ValidationError("O nome da família/responsável é obrigatório.")

    cleaned_cep = ViaCEPService.clean_cep(cep)
    formatted_cep = f"{cleaned_cep[:5]}-{cleaned_cep[5:]}"

    # Auto-fill address via ViaCEP if requested and address is incomplete
    if auto_fill_cep and (not street or not neighborhood or not city or not state):
        try:
            address_data = ViaCEPService.fetch_address(cleaned_cep)
            street = street or address_data.street
            neighborhood = neighborhood or address_data.neighborhood
            city = city or address_data.city
            state = state or address_data.state
            if not complement and address_data.complement:
                complement = address_data.complement
        except Exception:
            # If ViaCEP fails, user-provided fields are kept, but if still missing required fields, validation will flag it
            pass

    if not street:
        raise ValidationError("O logradouro/rua é obrigatório.")
    if not neighborhood:
        raise ValidationError("O bairro é obrigatório.")
    if not city:
        raise ValidationError("A cidade é obrigatória.")
    if not state:
        raise ValidationError("O estado (UF) é obrigatório.")
    if not number:
        raise ValidationError("O número do endereço é obrigatório.")

    family = Family(
        unit=unit,
        representative_name=representative_name,
        registration_date=registration_date or timezone.now().date(),
        cep=formatted_cep,
        street=street.strip(),
        number=str(number).strip(),
        complement=complement.strip(),
        neighborhood=neighborhood.strip(),
        city=city.strip(),
        state=state.strip().upper()[:2],
        monthly_income=monthly_income,
        housing_status=housing_status.strip(),
        notes=notes.strip(),
        is_active=is_active,
    )
    family.full_clean()
    family.save()
    return family


@transaction.atomic
def family_update(
    family: Family,
    *,
    representative_name: str | None = None,
    cep: str | None = None,
    street: str | None = None,
    number: str | None = None,
    complement: str | None = None,
    neighborhood: str | None = None,
    city: str | None = None,
    state: str | None = None,
    monthly_income: Decimal | float | int | None | object = ...,
    housing_status: str | None = None,
    notes: str | None = None,
    is_active: bool | None = None,
    actor_user: Any | None = None,
) -> Family:
    """
    Updates an existing Family record.
    """
    if actor_user and not has_unit_permission(actor_user, family.unit, PERM_REGISTER_BENEFICIARIES):
        raise PermissionDeniedError(
            f"Usuário '{actor_user}' não tem permissão para editar famílias na unidade '{family.unit.name}'."
        )

    if representative_name is not None:
        rep_name = representative_name.strip()
        if not rep_name:
            raise ValidationError("O nome da família/responsável não pode ser vazio.")
        family.representative_name = rep_name

    if cep is not None:
        cleaned_cep = ViaCEPService.clean_cep(cep)
        family.cep = f"{cleaned_cep[:5]}-{cleaned_cep[5:]}"

    if street is not None:
        family.street = street.strip()
    if number is not None:
        family.number = str(number).strip()
    if complement is not None:
        family.complement = complement.strip()
    if neighborhood is not None:
        family.neighborhood = neighborhood.strip()
    if city is not None:
        family.city = city.strip()
    if state is not None:
        family.state = state.strip().upper()[:2]
    if monthly_income is not ...:
        family.monthly_income = monthly_income  # type: ignore
    if housing_status is not None:
        family.housing_status = housing_status.strip()
    if notes is not None:
        family.notes = notes.strip()
    if is_active is not None:
        family.is_active = is_active

    family.full_clean()
    family.save()
    return family


@transaction.atomic
def family_member_create(
    *,
    family: Family,
    name: str,
    birth_date: datetime.date,
    kinship: str = Kinship.OTHER,
    marital_status: str = MaritalStatus.SINGLE,
    inclusion_date: datetime.date | None = None,
    cpf: str | None = None,
    notes: str = "",
    actor_user: Any | None = None,
) -> FamilyMember:
    """
    Creates and links a new member to a family.
    """
    if actor_user and not has_unit_permission(actor_user, family.unit, PERM_REGISTER_BENEFICIARIES):
        raise PermissionDeniedError(
            f"Usuário '{actor_user}' não tem permissão para cadastrar membros na unidade '{family.unit.name}'."
        )

    name = name.strip()
    if not name:
        raise ValidationError("O nome do membro é obrigatório.")

    if kinship not in Kinship.values:
        raise ValidationError(f"Grau de parentesco '{kinship}' inválido.")

    if marital_status not in MaritalStatus.values:
        raise ValidationError(f"Estado civil '{marital_status}' inválido.")

    member = FamilyMember(
        family=family,
        name=name,
        birth_date=birth_date,
        kinship=kinship,
        marital_status=marital_status,
        inclusion_date=inclusion_date or timezone.now().date(),
        cpf=cpf.strip() if cpf else None,
        notes=notes.strip(),
    )
    member.full_clean()
    member.save()
    return member


@transaction.atomic
def family_member_update(
    member: FamilyMember,
    *,
    name: str | None = None,
    birth_date: datetime.date | None = None,
    kinship: str | None = None,
    marital_status: str | None = None,
    cpf: str | None | object = ...,
    notes: str | None = None,
    actor_user: Any | None = None,
) -> FamilyMember:
    """
    Updates an existing family member.
    """
    if actor_user and not has_unit_permission(actor_user, member.family.unit, PERM_REGISTER_BENEFICIARIES):
        raise PermissionDeniedError(
            f"Usuário '{actor_user}' não tem permissão para editar membros na unidade '{member.family.unit.name}'."
        )

    if name is not None:
        n = name.strip()
        if not n:
            raise ValidationError("O nome do membro não pode ser vazio.")
        member.name = n

    if birth_date is not None:
        member.birth_date = birth_date

    if kinship is not None:
        if kinship not in Kinship.values:
            raise ValidationError(f"Grau de parentesco '{kinship}' inválido.")
        member.kinship = kinship

    if marital_status is not None:
        if marital_status not in MaritalStatus.values:
            raise ValidationError(f"Estado civil '{marital_status}' inválido.")
        member.marital_status = marital_status

    if cpf is not ...:
        member.cpf = cpf.strip() if cpf else None  # type: ignore

    if notes is not None:
        member.notes = notes.strip()

    member.full_clean()
    member.save()
    return member


@transaction.atomic
def family_member_delete(
    member: FamilyMember,
    *,
    actor_user: Any | None = None,
) -> None:
    """
    Deletes a family member.
    """
    if actor_user and not has_unit_permission(actor_user, member.family.unit, PERM_REGISTER_BENEFICIARIES):
        raise PermissionDeniedError(
            f"Usuário '{actor_user}' não tem permissão para excluir membros na unidade '{member.family.unit.name}'."
        )

    member.delete()
