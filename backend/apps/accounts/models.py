import uuid

from django.db import models


class EmailLoginChallenge(models.Model):
    challenge_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    email = models.EmailField(db_index=True)
    display_name = models.CharField(max_length=150, blank=True)
    code_hash = models.CharField(max_length=128)
    requested_ip = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Login challenge for {self.email}"
