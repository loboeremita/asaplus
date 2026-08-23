from __future__ import annotations

from django.db import models
from common.models import TimeStampedModel


class UnitType(models.TextChoices):
    UNION = "UNION", "União"
    CONFERENCE = "CONFERENCE", "Associação / Missão"
    DISTRICT = "DISTRICT", "Distrito"
    LOCAL_CHURCH = "LOCAL_CHURCH", "Igreja Local"
    OTHER = "OTHER", "Outro"


class OrganizationalUnit(TimeStampedModel):
    """
    Hierarchical organizational unit (e.g. Union -> Conference/Mission -> District -> Local Church).
    The root unit has parent=None, and any unit can have multiple child units.
    """

    name = models.CharField(
        max_length=255,
        verbose_name="Nome da Unidade",
        help_text="Nome descritivo da unidade (ex: Igreja Central de Salvador).",
    )
    code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Código da Unidade",
        help_text="Código identificador único opcional (ex: IAG-001).",
    )
    unit_type = models.CharField(
        max_length=30,
        choices=UnitType.choices,
        default=UnitType.LOCAL_CHURCH,
        verbose_name="Tipo de Unidade",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Unidade Superior (Pai)",
        help_text="Unidade hierarquicamente superior. Deixe em branco se for a raiz.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Ativo",
    )

    class Meta:
        verbose_name = "Unidade Organizacional"
        verbose_name_plural = "Unidades Organizacionais"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["parent", "is_active"]),
            models.Index(fields=["unit_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_unit_type_display()})"

    def get_ancestor_ids(self, include_self: bool = True) -> set[int]:
        """
        Returns a set of IDs for all ancestors of this unit, traversing up to the root.
        """
        ancestor_ids: set[int] = set()
        if include_self and self.pk:
            ancestor_ids.add(self.pk)

        current = self.parent
        visited: set[int] = set()
        while current is not None:
            if current.pk in visited:
                break  # guard against cycles
            visited.add(current.pk)
            ancestor_ids.add(current.pk)
            current = current.parent

        return ancestor_ids

    def get_ancestors(self, include_self: bool = True) -> list[OrganizationalUnit]:
        """
        Returns a list of all ancestor units ordered from closest parent up to root.
        """
        ancestors: list[OrganizationalUnit] = []
        if include_self:
            ancestors.append(self)

        current = self.parent
        visited: set[int] = set()
        while current is not None:
            if current.pk in visited:
                break
            visited.add(current.pk)
            ancestors.append(current)
            current = current.parent

        return ancestors

    def get_descendant_ids(self, include_self: bool = True) -> set[int]:
        """
        Returns a set of IDs for all descendant units, traversing down to all leaves.
        Uses BFS with batched querying for maximum database efficiency.
        """
        if not self.pk:
            return set()

        descendant_ids: set[int] = {self.pk} if include_self else set()
        current_level_ids = [self.pk]

        while current_level_ids:
            next_level_ids = list(
                OrganizationalUnit.objects.filter(parent_id__in=current_level_ids).values_list("id", flat=True)
            )
            if not next_level_ids:
                break
            descendant_ids.update(next_level_ids)
            current_level_ids = next_level_ids

        return descendant_ids

    def get_descendants(self, include_self: bool = True) -> models.QuerySet[OrganizationalUnit]:
        """
        Returns a QuerySet of all descendant units.
        """
        descendant_ids = self.get_descendant_ids(include_self=include_self)
        return OrganizationalUnit.objects.filter(id__in=descendant_ids)

    def is_ancestor_of(self, other_unit: OrganizationalUnit) -> bool:
        """
        Returns True if self is an ancestor of other_unit.
        """
        if not self.pk or not other_unit.pk:
            return False
        return self.pk in other_unit.get_ancestor_ids(include_self=False)

    def is_descendant_of(self, other_unit: OrganizationalUnit) -> bool:
        """
        Returns True if self is a descendant of other_unit.
        """
        if not self.pk or not other_unit.pk:
            return False
        return other_unit.is_ancestor_of(self)
