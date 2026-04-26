from django.db import models


class Worker(models.Model):
    name = models.CharField(max_length=100)
    vest_id = models.CharField(max_length=50, unique=True, db_index=True)
    zone = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.vest_id})"
