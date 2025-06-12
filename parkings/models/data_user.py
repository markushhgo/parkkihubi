from django.conf import settings
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from parkings.models.mixins import TimestampedModelMixin, UUIDPrimaryKeyMixin


class DataUser(TimestampedModelMixin, UUIDPrimaryKeyMixin):
    """
    A person who can fetch data through the Data API.
    """
    name = models.CharField(verbose_name=_("name"), max_length=80)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name=_("user")
    )

    class Meta:
        verbose_name = _("data user")
        verbose_name_plural = _("data users")

    def __str__(self):
        return self.name
