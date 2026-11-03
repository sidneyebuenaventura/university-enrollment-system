from django.conf import settings


class DatabaseRouter:
    """
    A router to control all database operations.
    """

    def __init__(self):
        self.mapping = settings.DATABASE_MAPPING

    def _get_db(self, model=None, app_label=None):
        for db, apps in self.mapping.items():
            if model:
                app_label = model._meta.app_label
            if app_label in apps:
                return db

    def db_for_read(self, model, **kwargs):
        return self._get_db(model)

    def db_for_write(self, model, **kwargs):
        return self._get_db(model)

    def allow_relation(self, obj1, obj2, **kwargs):
        obj1_db = self._get_db(obj1)
        obj2_db = self._get_db(obj2)
        return obj1_db == obj2_db

    def allow_migrate(self, db, app_label, model_name=None, **kwargs):
        app_db = self._get_db(app_label=app_label)

        if app_db:
            return app_db == db

        if db in self.mapping or app_db:
            return False
