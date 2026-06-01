import io
import re

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import StreamingHttpResponse

from .models import Report

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def extract_bearer_token(request):
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    prefix = "Bearer "
    if auth.startswith(prefix):
        return auth[len(prefix) :].strip()
    return None


def parse_filename(content_disposition, fallback):
    if not content_disposition:
        return fallback
    match = re.search(r'filename="?([^";\n]+)"?', content_disposition)
    return match.group(1) if match else fallback


def proxy_generate_report(request, report_type, date_from, date_to):
    """
    Forward report generation to the Node report-service and stream the .docx
    response back to the client. Returns (response, error_body, status_code).
    """
    api_token = extract_bearer_token(request)
    if not api_token:
        return None, {"detail": "Authentication credentials were not provided."}, 401

    payload = {
        "report_type": report_type,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "api_token": api_token,
    }

    try:
        upstream = requests.post(
            settings.REPORT_SERVICE_URL,
            json=payload,
            stream=True,
            timeout=settings.REPORT_SERVICE_TIMEOUT,
        )
    except requests.RequestException as exc:
        return None, {"detail": f"Report service unavailable: {exc}"}, 502

    if upstream.status_code != 200:
        upstream.close()
        try:
            error_body = upstream.json()
        except ValueError:
            error_body = {"detail": upstream.text or "Report service error."}
        status_code = upstream.status_code if 400 <= upstream.status_code < 600 else 502
        return None, error_body, status_code

    fallback_name = f"{report_type.lower()}_report_{date_from}_{date_to}.docx"
    filename = parse_filename(upstream.headers.get("Content-Disposition"), fallback_name)
    content_type = upstream.headers.get("Content-Type", DOCX_CONTENT_TYPE)

    def streaming_content():
        collected = io.BytesIO()
        try:
            for chunk in upstream.iter_content(chunk_size=8192):
                if chunk:
                    collected.write(chunk)
                    yield chunk
        finally:
            upstream.close()

        collected.seek(0)
        report = Report(
            report_type=report_type,
            date_from=date_from,
            date_to=date_to,
            created_by=request.user,
        )
        report.file.save(filename, ContentFile(collected.read()), save=True)

    response = StreamingHttpResponse(streaming_content(), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response, None, 200
