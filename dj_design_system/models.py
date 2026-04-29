from django.db import models


class GalleryPermission(models.Model):
    """Holder for gallery-related permissions. No database table is created."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ("can_view_gallery", "Can view the design system gallery"),
        ]
