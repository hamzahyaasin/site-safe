from rest_framework import serializers

from .models import Report


class ReportGenerateSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=Report.ReportType.choices)
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    file_format = serializers.ChoiceField(choices=Report.Format.choices, default=Report.Format.DOCX)
    tz = serializers.CharField(required=False, allow_blank=True, default="", max_length=64)

    def validate_tz(self, value):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        if not value:
            return ""
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise serializers.ValidationError("Unknown time zone.") from exc
        return value

    def validate(self, attrs):
        if attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError({"date_to": "End date must be on or after start date."})
        return attrs


class ReportSerializer(serializers.ModelSerializer):
    report_type_label = serializers.CharField(source="get_report_type_display", read_only=True)
    filename = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            "id",
            "report_type",
            "report_type_label",
            "file_format",
            "date_from",
            "date_to",
            "filename",
            "download_url",
            "created_at",
        )

    def get_filename(self, obj):
        return obj.file.name.split("/")[-1] if obj.file else ""

    def get_download_url(self, obj):
        request = self.context.get("request")
        if not request or not obj.file:
            return None
        return request.build_absolute_uri(f"/api/v1/reports/{obj.id}/download/")
