import datetime
import pytest
from django.db.models import ProtectedError
from benefits.exceptions import (
    BenefitAlreadyGrantedError,
    BenefitEditNotAllowedError,
    BenefitInactiveError,
    BenefitInheritanceError,
    BenefitProtectedError,
    BenefitScopeMismatchError,
)
from benefits.models import Benefit, BenefitPeriod, BenefitScope, BenefitType
from benefits.selectors import (
    benefit_get_available_for_unit,
)
from benefits.services import benefit_create, benefit_delete, benefit_grant_create, benefit_update
from beneficiaries.models import Family, FamilyMember, Kinship
from organizational.models import OrganizationalUnit, UnitType


@pytest.mark.django_db
class TestBenefits:
    @pytest.fixture
    def setup_data(self):
        conf = OrganizationalUnit.objects.create(name="Associação Bahia", unit_type=UnitType.CONFERENCE)
        church = OrganizationalUnit.objects.create(
            name="Igreja Liberdade", unit_type=UnitType.LOCAL_CHURCH, parent=conf
        )
        other_conf = OrganizationalUnit.objects.create(name="Outra Associação", unit_type=UnitType.CONFERENCE)
        other_church = OrganizationalUnit.objects.create(
            name="Outra Igreja", unit_type=UnitType.LOCAL_CHURCH, parent=other_conf
        )

        family = Family.objects.create(
            unit=church,
            representative_name="Família Pereira",
            cep="40000-000",
            street="Rua A",
            number="10",
            neighborhood="Centro",
            city="Salvador",
            state="BA",
        )
        member1 = FamilyMember.objects.create(
            family=family,
            name="João Pereira",
            birth_date=datetime.date(1990, 1, 1),
            kinship=Kinship.HEAD,
        )
        member2 = FamilyMember.objects.create(
            family=family,
            name="Ana Pereira",
            birth_date=datetime.date(1992, 2, 2),
            kinship=Kinship.SPOUSE,
        )

        return {
            "conf": conf,
            "church": church,
            "other_conf": other_conf,
            "other_church": other_church,
            "family": family,
            "member1": member1,
            "member2": member2,
        }

    def test_benefit_inheritance_and_availability(self, setup_data):
        # Benefit created at Conference level
        conf_benefit = benefit_create(
            name="Mutirão de Natal Estadual",
            unit=setup_data["conf"],
            benefit_type=BenefitType.CAMPANHA,
            period=BenefitPeriod.UNICO,
            scope=BenefitScope.FAMILIAR,
        )
        # Benefit created at Local Church level
        church_benefit = benefit_create(
            name="Cesta Básica Emergencial",
            unit=setup_data["church"],
            benefit_type=BenefitType.CESTA_BASICA,
            period=BenefitPeriod.MENSAL,
            scope=BenefitScope.FAMILIAR,
        )

        # Available for church: both its own and Conference's benefit
        church_available = benefit_get_available_for_unit(setup_data["church"])
        assert conf_benefit in church_available
        assert church_benefit in church_available

        # Available for other church: neither of the above
        other_available = benefit_get_available_for_unit(setup_data["other_church"])
        assert conf_benefit not in other_available
        assert church_benefit not in other_available

    def test_child_unit_cannot_edit_inherited_benefit(self, setup_data):
        conf_benefit = benefit_create(
            name="Projeto Inverno Aquecido",
            unit=setup_data["conf"],
            scope=BenefitScope.FAMILIAR,
        )

        # Church trying to edit Conference benefit
        with pytest.raises(BenefitEditNotAllowedError, match="não pode editar o benefício"):
            benefit_update(
                conf_benefit,
                name="Nome Alterado pela Igreja",
                actor_unit=setup_data["church"],
            )

        # Conference editing its own benefit should succeed
        updated = benefit_update(
            conf_benefit,
            name="Projeto Inverno Aquecido 2026",
            actor_unit=setup_data["conf"],
        )
        assert updated.name == "Projeto Inverno Aquecido 2026"

    def test_cannot_grant_inactive_benefit(self, setup_data):
        inactive_benefit = benefit_create(
            name="Curso Encerrado",
            unit=setup_data["church"],
            scope=BenefitScope.FAMILIAR,
            is_active=False,
        )

        with pytest.raises(BenefitInactiveError, match="está inativo"):
            benefit_grant_create(
                benefit=inactive_benefit,
                family=setup_data["family"],
                grant_unit=setup_data["church"],
            )

    def test_cannot_grant_unrelated_benefit(self, setup_data):
        unrelated_benefit = benefit_create(
            name="Auxílio Outra Associação",
            unit=setup_data["other_conf"],
            scope=BenefitScope.FAMILIAR,
        )

        with pytest.raises(BenefitInheritanceError, match="não pertence à hierarquia"):
            benefit_grant_create(
                benefit=unrelated_benefit,
                family=setup_data["family"],
                grant_unit=setup_data["church"],
            )

    def test_familiar_scope_single_grant_rule(self, setup_data):
        familiar_benefit = benefit_create(
            name="Cesta de Natal 2026",
            unit=setup_data["conf"],
            scope=BenefitScope.FAMILIAR,
        )

        # First grant should succeed
        grant = benefit_grant_create(
            benefit=familiar_benefit,
            family=setup_data["family"],
            grant_unit=setup_data["church"],
        )
        assert grant.benefit == familiar_benefit
        assert grant.family == setup_data["family"]
        assert grant.member is None

        # Trying to grant familiar benefit with a member should fail
        with pytest.raises(BenefitScopeMismatchError, match="escopo familiar e não deve ser atribuído a um membro"):
            benefit_grant_create(
                benefit=familiar_benefit,
                family=setup_data["family"],
                grant_unit=setup_data["church"],
                member=setup_data["member1"],
            )

        # Trying to grant familiar benefit again to the same family must fail
        with pytest.raises(BenefitAlreadyGrantedError, match="já foi concedido anteriormente"):
            benefit_grant_create(
                benefit=familiar_benefit,
                family=setup_data["family"],
                grant_unit=setup_data["church"],
            )

    def test_individual_scope_grant_rule(self, setup_data):
        individual_benefit = benefit_create(
            name="Curso de Eletricista",
            unit=setup_data["conf"],
            benefit_type=BenefitType.PROFISSIONALIZANTE,
            scope=BenefitScope.INDIVIDUAL,
        )

        # Grant without member should fail
        with pytest.raises(BenefitScopeMismatchError, match="escopo individual e exige a seleção de um membro"):
            benefit_grant_create(
                benefit=individual_benefit,
                family=setup_data["family"],
                grant_unit=setup_data["church"],
                member=None,
            )

        # Grant to member1
        grant1 = benefit_grant_create(
            benefit=individual_benefit,
            family=setup_data["family"],
            grant_unit=setup_data["church"],
            member=setup_data["member1"],
        )
        assert grant1.member == setup_data["member1"]

        # Grant to member2 of the same family can also receive the individual benefit
        grant2 = benefit_grant_create(
            benefit=individual_benefit,
            family=setup_data["family"],
            grant_unit=setup_data["church"],
            member=setup_data["member2"],
        )
        assert grant2.member == setup_data["member2"]

    def test_protected_deletion_when_grants_exist(self, setup_data):
        benefit = benefit_create(
            name="Auxílio Transporte",
            unit=setup_data["church"],
            scope=BenefitScope.FAMILIAR,
        )

        # Before grants, deletion works
        benefit_temp = benefit_create(
            name="Benefício Temporário",
            unit=setup_data["church"],
            scope=BenefitScope.FAMILIAR,
        )
        benefit_delete(benefit_temp)
        assert not Benefit.objects.filter(id=benefit_temp.id).exists()

        # After grant, service blocks deletion
        benefit_grant_create(
            benefit=benefit,
            family=setup_data["family"],
            grant_unit=setup_data["church"],
        )

        with pytest.raises(BenefitProtectedError, match="possui concessões históricas"):
            benefit_delete(benefit)

        # Model-level direct delete should also be protected by models.PROTECT
        with pytest.raises(ProtectedError):
            benefit.delete()

    def test_quantity_stock_decrement(self, setup_data):
        benefit = benefit_create(
            name="Kit Escolar",
            unit=setup_data["church"],
            scope=BenefitScope.INDIVIDUAL,
            quantity_available=2,
        )

        benefit_grant_create(
            benefit=benefit,
            family=setup_data["family"],
            grant_unit=setup_data["church"],
            member=setup_data["member1"],
            quantity=1,
        )
        benefit.refresh_from_db()
        assert benefit.quantity_available == 1

        benefit_grant_create(
            benefit=benefit,
            family=setup_data["family"],
            grant_unit=setup_data["church"],
            member=setup_data["member2"],
            quantity=1,
        )
        benefit.refresh_from_db()
        assert benefit.quantity_available == 0

    def test_benefit_selectors_and_grants_queries(self, setup_data):
        from benefits.selectors import (
            benefit_get_by_id,
            benefit_get_grants_by_unit,
            benefit_get_grants_for_family,
            benefit_get_grants_for_member,
            benefit_list_created_by_unit,
        )

        b = benefit_create(
            name="Ajuda Emergencial",
            unit=setup_data["church"],
            scope=BenefitScope.INDIVIDUAL,
        )
        assert benefit_get_by_id(b.id) == b
        assert b in benefit_list_created_by_unit(setup_data["church"])

        grant = benefit_grant_create(
            benefit=b,
            family=setup_data["family"],
            grant_unit=setup_data["church"],
            member=setup_data["member1"],
        )

        assert grant in benefit_get_grants_for_family(setup_data["family"])
        assert grant in benefit_get_grants_for_member(setup_data["member1"])
        assert grant in benefit_get_grants_by_unit(setup_data["church"])

