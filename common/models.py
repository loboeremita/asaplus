from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model providing self-updating
    created_at and updated_at timestamp fields.
    """

    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        db_index=True,
        verbose_name="Criado em",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em",
    )

    class Meta:
        abstract = True
