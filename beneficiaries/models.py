from django.db import models
from django.utils import timezone
from common.models import TimeStampedModel


class MaritalStatus(models.TextChoices):
    SINGLE = "SINGLE", "Solteiro(a)"
    MARRIED = "MARRIED", "Casado(a)"
    DIVORCED = "DIVORCED", "Divorciado(a)"
    WIDOWED = "WIDOWED", "Viúvo(a)"
    STABLE_UNION = "STABLE_UNION", "União Estável)"
    OTHER = "OTHER", "Outro"


class Kinship(models.TextChoices):
    HEAD = "HEAD", "Responsável Familiar"
    SPOUSE = "SPOUSE", "Cônjuge / Companheiro(a)"
    SON_DAUGHTER = "SON_DAUGHTER", "Filho(a)"
    PARENT = "PARENT", "Pai / Mãe"
    SIBLING = "SIBLING", "Irmão / Irmã"
    GRANDPARENT = "GRANDPARENT", "Avô / Avó"
    GRANDCHILD = "GRANDCHILD", "Neto(a)"
    OTHER = "OTHER", "Outro Vínculo"


class Family(TimeStampedModel):
    """
    Represents an assisted family linked to a specific Organizational Unit.
    """

    unit = models.ForeignKey(
        "organizational.OrganizationalUnit",
        on_delete=models.PROTECT,
        related_name="families",
        verbose_name="Unidade Responsável",
        help_text="Unidade que acompanha e atende esta família.",
    )
    representative_name = models.CharField(
        max_length=255,
        verbose_name="Nome do Responsável / Família",
        help_text="Nome da família ou do responsável principal.",
    )
    registration_date = models.DateField(
        default=timezone.now,
        verbose_name="Data de Cadastro",
    )

    # Address fields
    cep = models.CharField(
        max_length=9,
        db_index=True,
        verbose_name="CEP",
        help_text="CEP no formato 00000-000 ou 00000000.",
    )
    street = models.CharField(
        max_length=255,
        verbose_name="Logradouro / Rua",
    )
    number = models.CharField(
        max_length=50,
        verbose_name="Número",
    )
    complement = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Complemento",
    )
    neighborhood = models.CharField(
        max_length=100,
        verbose_name="Bairro",
    )
    city = models.CharField(
        max_length=100,
        verbose_name="Cidade",
    )
    state = models.CharField(
        max_length=2,
        verbose_name="UF",
    )

    # Socioeconomic information
    monthly_income = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Renda Familiar Mensal (R$)",
    )
    housing_status = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Situação de Moradia",
        help_text="Ex: Própria, Alugada, Cedida, Ocupação.",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Observações Socioeconômicas",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Ativo",
    )

    class Meta:
        verbose_name = "Família"
        verbose_name_plural = "Famílias"
        ordering = ["-registration_date", "representative_name"]
        indexes = [
            models.Index(fields=["unit", "is_active"]),
            models.Index(fields=["cep"]),
            models.Index(fields=["representative_name"]),
        ]

    def __str__(self) -> str:
        return f"{self.representative_name} ({self.unit.name})"

    @property
    def full_address(self) -> str:
        comp = f", {self.complement}" if self.complement else ""
        return f"{self.street}, {self.number}{comp} - {self.neighborhood}, {self.city}/{self.state} - CEP {self.cep}"


class FamilyMember(TimeStampedModel):
    """
    Individual member of a family.
    """

    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name="Família",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Nome Completo",
    )
    birth_date = models.DateField(
        verbose_name="Data de Nascimento",
    )
    inclusion_date = models.DateField(
        default=timezone.now,
        verbose_name="Data de Inclusão",
    )
    marital_status = models.CharField(
        max_length=30,
        choices=MaritalStatus.choices,
        default=MaritalStatus.SINGLE,
        verbose_name="Estado Civil",
    )
    kinship = models.CharField(
        max_length=30,
        choices=Kinship.choices,
        default=Kinship.OTHER,
        verbose_name="Grau de Parentesco",
    )
    cpf = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        verbose_name="CPF",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Observações do Membro",
    )

    class Meta:
        verbose_name = "Membro da Família"
        verbose_name_plural = "Membros da Família"
        ordering = ["inclusion_date", "name"]
        indexes = [
            models.Index(fields=["family", "kinship"]),
            models.Index(fields=["cpf"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_kinship_display()} - {self.family.representative_name})"
