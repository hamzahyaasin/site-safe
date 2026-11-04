from django.apps import AppConfig


class SitemapConfig(AppConfig):
    name = 'sitemap'

    def ready(self):
        import sitemap.signals  # noqa: F401
