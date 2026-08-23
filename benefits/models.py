from django.conf import settings
from django.db import models
from django.utils import timezone
from common.models import TimeStampedModel


def get_current_year() -> int:
    return timezone.now().year


class BenefitType(models.TextChoices):
    AJUDA = "AJUDA", "Ajuda de Custo / Financeira"
    CAMPANHA = "CAMPANHA", "Campanha Sazonal (Natal, Inverno, etc.)"
    CESTA_BASICA = "CESTA_BASICA", "Cesta Básica / Alimentos"
    PROFISSIONALIZANTE = "PROFISSIONALIZANTE", "Curso Profissionalizante"
    ROUPAS = "ROUPAS", "Roupas e Calçados"
    OUTRO = "OUTRO", "Outro"


class BenefitPeriod(models.TextChoices):
    UNICO = "UNICO", "Único (Pontual)"
    QUINZENAL = "QUINZENAL", "Quinzenal"
    MENSAL = "MENSAL", "Mensal"
    TRIMESTRAL = "TRIMESTRAL", "Trimestral"
    SEMESTRAL = "SEMESTRAL", "Semestral"
    ANUAL = "ANUAL", "Anual"


class BenefitScope(models.TextChoices):
    FAMILIAR = "FAMILIAR", "Familiar"
    INDIVIDUAL = "INDIVIDUAL", "Individual"


class Benefit(TimeStampedModel):
    """
    Represents a social benefit, campaign, or assistance project.
    Can be created at any organizational level (Union, Conference, District, Church)
    and is automatically inherited by all descendant units.
    """

    name = models.CharField(
        max_length=255,
        verbose_name="Nome do Benefício",
    )
    year = models.PositiveIntegerField(
        default=get_current_year,
        db_index=True,
        verbose_name="Ano de Referência",
    )
    benefit_type = models.CharField(
        max_length=30,
        choices=BenefitType.choices,
        default=BenefitType.CESTA_BASICA,
        verbose_name="Tipo de Benefício",
    )
    period = models.CharField(
        max_length=30,
        choices=BenefitPeriod.choices,
        default=BenefitPeriod.UNICO,
        verbose_name="Periodicidade",
    )
    scope = models.CharField(
        max_length=20,
        choices=BenefitScope.choices,
        default=BenefitScope.FAMILIAR,
        db_index=True,
        verbose_name="Escopo da Concessão",
        help_text="Familiar: concedido à família como um todo (1x). Individual: concedido a um membro específico.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Ativo",
    )
    unit = models.ForeignKey(
        "organizational.OrganizationalUnit",
        on_delete=models.PROTECT,
        related_name="created_benefits",
        verbose_name="Unidade de Origem",
        help_text="Unidade que criou e gerencia este benefício.",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descrição e Critérios",
    )
    quantity_available = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Quantidade Total Disponível (Opcional)",
    )

    class Meta:
        verbose_name = "Benefício"
        verbose_name_plural = "Benefícios"
        ordering = ["-year", "name"]
        indexes = [
            models.Index(fields=["unit", "is_active"]),
            models.Index(fields=["scope", "is_active"]),
            models.Index(fields=["year", "benefit_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.year}) - {self.get_scope_display()} [{self.unit.name}]"


class BenefitGrant(TimeStampedModel):
    """
    Represents the actual concession/granting of a benefit to a family or family member.
    Deletions of benefits with grants are blocked via models.PROTECT.
    """

    benefit = models.ForeignKey(
        Benefit,
        on_delete=models.PROTECT,
        related_name="grants",
        verbose_name="Benefício Concedido",
    )
    family = models.ForeignKey(
        "beneficiaries.Family",
        on_delete=models.PROTECT,
        related_name="benefit_grants",
        verbose_name="Família Beneficiada",
    )
    member = models.ForeignKey(
        "beneficiaries.FamilyMember",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="benefit_grants",
        verbose_name="Membro Beneficiado (se escopo individual)",
    )
    grant_unit = models.ForeignKey(
        "organizational.OrganizationalUnit",
        on_delete=models.PROTECT,
        related_name="unit_benefit_grants",
        verbose_name="Unidade Concessora",
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="granted_benefits",
        verbose_name="Concedido por (Usuário)",
    )
    granted_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="Data/Hora da Concessão",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantidade Concedida",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Observações da Concessão",
    )

    class Meta:
        verbose_name = "Concessão de Benefício"
        verbose_name_plural = "Concessões de Benefícios"
        ordering = ["-granted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["benefit", "family"],
                condition=models.Q(member__isnull=True),
                name="unique_familiar_benefit_grant_per_family",
            )
        ]
        indexes = [
            models.Index(fields=["benefit", "granted_at"]),
            models.Index(fields=["family", "granted_at"]),
            models.Index(fields=["grant_unit", "granted_at"]),
        ]

    def __str__(self) -> str:
        target = self.member.name if self.member else self.family.representative_name
        return f"Concessão: {self.benefit.name} para {target} em {self.granted_at.strftime('%d/%m/%Y')}"
