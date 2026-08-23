from __future__ import annotations

from django.db import transaction
from common.exceptions import BusinessRuleViolationError, ValidationError
from organizational.models import OrganizationalUnit, UnitType


@transaction.atomic
def unit_create(
    *,
    name: str,
    unit_type: str = UnitType.LOCAL_CHURCH,
    parent: OrganizationalUnit | None = None,
    code: str | None = None,
    is_active: bool = True,
) -> OrganizationalUnit:
    """
    Creates a new organizational unit.
    """
    name = name.strip()
    if not name:
        raise ValidationError("O nome da unidade é obrigatório.")

    if unit_type not in UnitType.values:
        raise ValidationError(f"Tipo de unidade '{unit_type}' inválido.")

    if code:
        code = code.strip()
        if OrganizationalUnit.objects.filter(code=code).exists():
            raise ValidationError(f"Já existe uma unidade cadastrada com o código '{code}'.")

    unit = OrganizationalUnit(
        name=name,
        unit_type=unit_type,
        parent=parent,
        code=code or None,
        is_active=is_active,
    )
    unit.full_clean()
    unit.save()
    return unit


@transaction.atomic
def unit_update(
    unit: OrganizationalUnit,
    *,
    name: str | None = None,
    unit_type: str | None = None,
    parent: OrganizationalUnit | None | object = ...,
    code: str | None | object = ...,
    is_active: bool | None = None,
) -> OrganizationalUnit:
    """
    Updates an organizational unit, preventing cyclical hierarchies.
    """
    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError("O nome da unidade não pode ficar em branco.")
        unit.name = name

    if unit_type is not None:
        if unit_type not in UnitType.values:
            raise ValidationError(f"Tipo de unidade '{unit_type}' inválido.")
        unit.unit_type = unit_type

    if parent is not ...:
        new_parent: OrganizationalUnit | None = parent  # type: ignore
        if new_parent is not None:
            if new_parent.pk == unit.pk:
                raise BusinessRuleViolationError("Uma unidade não pode ser pai de si mesma.")
            if new_parent.pk in unit.get_descendant_ids(include_self=False):
                raise BusinessRuleViolationError(
                    "Não é permitido mover uma unidade para ser filha de um de seus próprios descendentes."
                )
        unit.parent = new_parent

    if code is not ...:
        new_code: str | None = code  # type: ignore
        if new_code:
            new_code = new_code.strip()
            if (
                OrganizationalUnit.objects.filter(code=new_code)
                .exclude(pk=unit.pk)
                .exists()
            ):
                raise ValidationError(f"Já existe outra unidade com o código '{new_code}'.")
            unit.code = new_code
        else:
            unit.code = None

    if is_active is not None:
        unit.is_active = is_active

    unit.full_clean()
    unit.save()
    return unit


@transaction.atomic
def unit_delete(unit: OrganizationalUnit) -> None:
    """
    Deletes an organizational unit.
    """
    unit.delete()
