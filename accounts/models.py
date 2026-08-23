from django.conf import settings
from django.db import models
from common.models import TimeStampedModel


class RoleType(models.TextChoices):
    ADMIN = "ADMIN", "Administrador"
    PASTOR = "PASTOR", "Pastor"
    DIRECTOR = "DIRECTOR", "Diretor"
    SECRETARY = "SECRETARY", "Secretário"
    ASSISTANT = "ASSISTANT", "Auxiliar"


class UnitMembership(TimeStampedModel):
    """
    Associates a User with an OrganizationalUnit and defines their Role.
    Permissions are exercised on the assigned unit and inherited by all of its descendant units.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="unit_memberships",
        verbose_name="Usuário",
    )
    unit = models.ForeignKey(
        "organizational.OrganizationalUnit",
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Unidade Organizacional",
    )
    role = models.CharField(
        max_length=30,
        choices=RoleType.choices,
        default=RoleType.ASSISTANT,
        verbose_name="Papel / Função",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Ativo",
    )

    class Meta:
        verbose_name = "Vínculo de Usuário na Unidade"
        verbose_name_plural = "Vínculos de Usuários nas Unidades"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "unit"],
                name="unique_user_unit_membership",
            )
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["unit", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.get_role_display()} em {self.unit.name}"
