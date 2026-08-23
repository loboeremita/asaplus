import datetime
import pytest
from beneficiaries.models import Family, FamilyMember, Kinship
from beneficiaries.selectors import family_get_aggregated_benefits
from benefits.models import BenefitScope, BenefitType
from benefits.services import benefit_create, benefit_grant_create
from organizational.models import OrganizationalUnit, UnitType


@pytest.mark.django_db
class TestAggregatedFamilyBenefits:
    def test_family_aggregated_benefits_view(self):
        church = OrganizationalUnit.objects.create(name="Igreja Central", unit_type=UnitType.LOCAL_CHURCH)

        family = Family.objects.create(
            unit=church,
            representative_name="Família Albuquerque",
            cep="40020-000",
            street="Rua das Palmeiras",
            number="500",
            neighborhood="Barra",
            city="Salvador",
            state="BA",
        )

        FamilyMember.objects.create(
            family=family,
            name="Roberto Albuquerque",
            birth_date=datetime.date(1975, 4, 12),
            kinship=Kinship.HEAD,
        )
        mother = FamilyMember.objects.create(
            family=family,
            name="Clara Albuquerque",
            birth_date=datetime.date(1978, 9, 30),
            kinship=Kinship.SPOUSE,
        )
        son = FamilyMember.objects.create(
            family=family,
            name="Lucas Albuquerque",
            birth_date=datetime.date(2005, 1, 15),
            kinship=Kinship.SON_DAUGHTER,
        )

        # Benefits
        b_cesta = benefit_create(
            name="Cesta Básica Mensal",
            unit=church,
            benefit_type=BenefitType.CESTA_BASICA,
            scope=BenefitScope.FAMILIAR,
        )
        b_curso = benefit_create(
            name="Curso de Informática",
            unit=church,
            benefit_type=BenefitType.PROFISSIONALIZANTE,
            scope=BenefitScope.INDIVIDUAL,
        )
        b_roupas = benefit_create(
            name="Bazar Solidário",
            unit=church,
            benefit_type=BenefitType.ROUPAS,
            scope=BenefitScope.INDIVIDUAL,
        )

        # Grant concessions
        # 1. Familiar benefit to whole family
        benefit_grant_create(
            benefit=b_cesta,
            family=family,
            grant_unit=church,
            notes="Entrega de alimentos do mês de agosto",
        )
        # 2. Individual benefit to son
        benefit_grant_create(
            benefit=b_curso,
            family=family,
            grant_unit=church,
            member=son,
            notes="Vaga para módulo básico",
        )
        # 3. Individual benefit to mother
        benefit_grant_create(
            benefit=b_roupas,
            family=family,
            grant_unit=church,
            member=mother,
            notes="Peças de inverno",
        )

        overview = family_get_aggregated_benefits(family)

        assert overview["family_id"] == family.id
        assert overview["representative_name"] == "Família Albuquerque"
        assert overview["unit_name"] == "Igreja Central"
        assert overview["total_grants_count"] == 3
        assert overview["distinct_benefits_count"] == 3
        assert len(overview["grants"]) == 3

        # Check that both family-scoped and individual-scoped grants are present in the aggregated timeline
        grant_names = [g["benefit_name"] for g in overview["grants"]]
        assert "Cesta Básica Mensal" in grant_names
        assert "Curso de Informática" in grant_names
        assert "Bazar Solidário" in grant_names

        # Check recipient formatting
        recipients = [g["recipient_name"] for g in overview["grants"]]
        assert any("Família: Família Albuquerque" in r for r in recipients)
        assert any("Lucas Albuquerque" in r for r in recipients)
        assert any("Clara Albuquerque" in r for r in recipients)
