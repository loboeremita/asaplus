import datetime
from decimal import Decimal
from unittest.mock import patch
import pytest
from beneficiaries.models import Kinship, MaritalStatus
from beneficiaries.selectors import family_get_by_id, family_get_members, family_list_by_unit
from beneficiaries.services.family import (
    family_create,
    family_member_create,
    family_member_delete,
    family_member_update,
)
from beneficiaries.services.viacep import AddressData
from organizational.models import OrganizationalUnit, UnitType


@pytest.mark.django_db
class TestBeneficiaries:
    @pytest.fixture
    def church(self):
        return OrganizationalUnit.objects.create(name="Igreja Central", unit_type=UnitType.LOCAL_CHURCH)

    @patch("beneficiaries.services.viacep.ViaCEPService.fetch_address")
    def test_create_family_with_viacep_autofill(self, mock_fetch, church):
        mock_fetch.return_value = AddressData(
            cep="40020-000",
            street="Avenida Central",
            neighborhood="Centro Histórico",
            city="Salvador",
            state="BA",
            complement="Apto 101",
        )

        family = family_create(
            unit=church,
            representative_name="Família Santos",
            cep="40020000",
            number="150",
            monthly_income=Decimal("1800.00"),
            housing_status="Alugada",
        )

        assert family.representative_name == "Família Santos"
        assert family.unit == church
        assert family.street == "Avenida Central"
        assert family.neighborhood == "Centro Histórico"
        assert family.city == "Salvador"
        assert family.state == "BA"
        assert family.number == "150"
        assert family.monthly_income == Decimal("1800.00")
        assert family.is_active is True

    def test_create_family_member_and_relationship(self, church):
        family = family_create(
            unit=church,
            representative_name="Família Oliveira",
            cep="40000-000",
            street="Rua das Flores",
            number="42",
            neighborhood="Brotas",
            city="Salvador",
            state="BA",
            auto_fill_cep=False,
        )

        head = family_member_create(
            family=family,
            name="Carlos Oliveira",
            birth_date=datetime.date(1980, 5, 10),
            kinship=Kinship.HEAD,
            marital_status=MaritalStatus.MARRIED,
            cpf="123.456.789-00",
        )

        spouse = family_member_create(
            family=family,
            name="Maria Oliveira",
            birth_date=datetime.date(1985, 8, 22),
            kinship=Kinship.SPOUSE,
            marital_status=MaritalStatus.MARRIED,
        )

        child = family_member_create(
            family=family,
            name="Pedro Oliveira",
            birth_date=datetime.date(2012, 11, 3),
            kinship=Kinship.SON_DAUGHTER,
            marital_status=MaritalStatus.SINGLE,
        )

        members = family_get_members(family)
        assert members.count() == 3
        assert list(members) == [head, spouse, child]

        # Update member
        family_member_update(child, notes="Cursando ensino fundamental")
        child.refresh_from_db()
        assert child.notes == "Cursando ensino fundamental"

        # Delete member
        family_member_delete(child)
        assert family_get_members(family).count() == 2

    def test_family_selectors(self, church):
        f1 = family_create(
            unit=church,
            representative_name="Família A",
            cep="40000-000",
            street="Rua 1",
            number="1",
            neighborhood="Centro",
            city="Salvador",
            state="BA",
            auto_fill_cep=False,
        )
        f2 = family_create(
            unit=church,
            representative_name="Família B",
            cep="40000-000",
            street="Rua 2",
            number="2",
            neighborhood="Centro",
            city="Salvador",
            state="BA",
            auto_fill_cep=False,
            is_active=False,
        )

        assert family_get_by_id(f1.id) == f1
        active_families = family_list_by_unit(church, active_only=True)
        assert f1 in active_families
        assert f2 not in active_families

    def test_family_update_and_validations(self, church):
        from common.exceptions import ValidationError
        from beneficiaries.services.family import family_update

        family = family_create(
            unit=church,
            representative_name="Família Silva",
            cep="40000-000",
            street="Rua Original",
            number="10",
            neighborhood="Centro",
            city="Salvador",
            state="BA",
            auto_fill_cep=False,
        )

        updated = family_update(
            family,
            representative_name="Família Silva Nova",
            street="Rua Atualizada",
            housing_status="Própria",
        )
        assert updated.representative_name == "Família Silva Nova"
        assert updated.street == "Rua Atualizada"
        assert updated.housing_status == "Própria"

        with pytest.raises(ValidationError):
            family_update(family, representative_name="")

