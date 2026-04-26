from rest_framework import serializers

from .models import Worker


class WorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ("id", "name", "vest_id", "zone", "is_active", "created_at")
        read_only_fields = ("id", "created_at")
