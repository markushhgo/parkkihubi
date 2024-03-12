from django.apps import AppConfig


class ParkingsAppConfig(AppConfig):
    name = 'parkings'

    def ready(self):
        # register signals
        from parkings import signals  # noqa: F401
