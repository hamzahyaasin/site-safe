from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Report
from .proxy import proxy_generate_report
from .serializers import ReportGenerateSerializer, ReportSerializer


class ReportListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reports = Report.objects.all()
        serializer = ReportSerializer(reports, many=True, context={"request": request})
        return Response(serializer.data)


class GenerateReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReportGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        response, error_body, status_code = proxy_generate_report(
            request,
            data["report_type"],
            data["date_from"],
            data["date_to"],
        )
        if error_body is not None:
            return Response(error_body, status=status_code)
        return response


class ReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            report = Report.objects.get(pk=pk)
        except Report.DoesNotExist:
            return Response({"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND)

        if not report.file:
            return Response({"detail": "File not available."}, status=status.HTTP_404_NOT_FOUND)

        filename = report.file.name.split("/")[-1]
        with report.file.open("rb") as fh:
            content = fh.read()
        return HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
