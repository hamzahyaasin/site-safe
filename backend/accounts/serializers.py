from rest_framework import serializers

from .models import User, UserPreferences


class ProfileSerializer(serializers.ModelSerializer):
    notify_push = serializers.BooleanField(required=False)
    notify_email = serializers.BooleanField(required=False)

    class Meta:
        model = User
        fields = ("email", "full_name", "notify_push", "notify_email")
        read_only_fields = ("email", "full_name")

    def to_representation(self, instance):
        prefs, _ = UserPreferences.objects.get_or_create(user=instance)
        return {
            "email": instance.email,
            "full_name": instance.full_name,
            "notify_push": prefs.notify_push,
            "notify_email": prefs.notify_email,
        }

    def update(self, instance, validated_data):
        notify_push = validated_data.pop("notify_push", None)
        notify_email = validated_data.pop("notify_email", None)
        prefs, _ = UserPreferences.objects.get_or_create(user=instance)
        if notify_push is not None:
            prefs.notify_push = notify_push
        if notify_email is not None:
            prefs.notify_email = notify_email
        prefs.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
