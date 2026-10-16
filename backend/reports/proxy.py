import re

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpResponse

from .models import Report

CONTENT_TYPES = {
    Report.Format.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    Report.Format.PDF: "application/pdf",
}
# Generated reports are small; anything larger indicates a fault upstream.
MAX_REPORT_BYTES = 50 * 1024 * 1024


def content_type_for(file_format):
    return CONTENT_TYPES.get(file_format, "application/octet-stream")


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


def _error_body(upstream):
    try:
        return upstream.json()
    except ValueError:
        return {"detail": (upstream.text or "Report service error.")[:1000]}


def proxy_generate_report(request, report_type, date_from, date_to, file_format, tz=""):
    """
    Ask the Node report service for a document, store it, then return it.

    The whole document is received and saved before anything is sent to the
    browser, so report history is complete even if the download is
    interrupted, and a failed or truncated generation is never recorded.
    Returns (response, error_body, status_code).
    """
    api_token = extract_bearer_token(request)
    if not api_token:
        return None, {"detail": "Authentication credentials were not provided."}, 401

    payload = {
        "report_type": report_type,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "format": file_format,
        "tz": tz,
        "api_token": api_token,
    }

    try:
        upstream = requests.post(
            settings.REPORT_SERVICE_URL,
            json=payload,
            timeout=settings.REPORT_SERVICE_TIMEOUT,
        )
    except requests.RequestException as exc:
        return None, {"detail": f"Report service unavailable: {exc}"}, 502

    if upstream.status_code != 200:
        status_code = upstream.status_code if 400 <= upstream.status_code < 600 else 502
        return None, _error_body(upstream), status_code

    content = upstream.content
    expected = content_type_for(file_format)
    if not content or len(content) > MAX_REPORT_BYTES:
        return None, {"detail": "Report service returned an empty or oversized document."}, 502
    if upstream.headers.get("Content-Type", "").split(";")[0] != expected:
        return None, {"detail": "Report service returned an unexpected document type."}, 502

    extension = file_format.lower()
    fallback_name = f"{report_type.lower()}_report_{date_from}_{date_to}.{extension}"
    filename = parse_filename(upstream.headers.get("Content-Disposition"), fallback_name)

    report = Report(
        report_type=report_type,
        file_format=file_format,
        date_from=date_from,
        date_to=date_to,
        created_by=request.user,
    )
    report.file.save(filename, ContentFile(content), save=True)

    response = HttpResponse(content, content_type=expected)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response, None, 200
