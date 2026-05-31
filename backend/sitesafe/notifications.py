import logging

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging

from accounts.models import FCMToken

logger = logging.getLogger(__name__)


def _init_firebase():
    try:
        firebase_admin.get_app()
        return True
    except ValueError:
        pass

    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if not cred_path:
        logger.debug("FIREBASE_CREDENTIALS_PATH not set; push notifications disabled")
        return False

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    return True


def send_push_notification(user_ids, title, body, data=None):
    if not user_ids or not _init_firebase():
        return

    tokens = list(
        FCMToken.objects.filter(user_id__in=user_ids, is_active=True)
        .values_list("token", flat=True)
    )
    if not tokens:
        return

    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
    )
    response = messaging.send_each_for_multicast(message)
    for i, send_response in enumerate(response.responses):
        if not send_response.success:
            FCMToken.objects.filter(token=tokens[i]).update(is_active=False)
