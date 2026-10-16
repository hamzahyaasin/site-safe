from django.apps import AppConfig


class WorkersConfig(AppConfig):
    name = 'workers'

    def ready(self):
        import workers.signals  # noqa: F401
