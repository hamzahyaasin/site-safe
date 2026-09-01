from rest_framework import serializers

from .models import Role, User, UserPreferences


class ProfileSerializer(serializers.ModelSerializer):
    notify_push = serializers.BooleanField(required=False)
    notify_email = serializers.BooleanField(required=False)
    # Effective role, not the raw column: a legacy superuser or is_admin
    # account resolves to Admin even if its role was never set.
    role = serializers.SerializerMethodField()
    role_label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("email", "full_name", "role", "role_label", "notify_push", "notify_email")
        read_only_fields = ("email", "full_name", "role", "role_label")

    def get_role(self, obj):
        if obj.is_superuser or obj.is_admin:
            return Role.ADMIN.value
        return obj.role

    def get_role_label(self, obj):
        return Role(self.get_role(obj)).label

    def to_representation(self, instance):
        # NB: this builds the payload by hand rather than deferring to
        # Meta.fields, so any new field must be added here as well.
        prefs, _ = UserPreferences.objects.get_or_create(user=instance)
        return {
            "email": instance.email,
            "full_name": instance.full_name,
            "role": self.get_role(instance),
            "role_label": self.get_role_label(instance),
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
