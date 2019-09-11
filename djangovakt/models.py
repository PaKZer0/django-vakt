import uuid

from django.contrib.postgres.fields import JSONField
from django.db import models

# Create your models here.
class Policy(models.Model):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doc = JSONField()
