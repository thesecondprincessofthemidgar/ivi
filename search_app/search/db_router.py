class MediaRouter:
    app_label = 'search'

    def db_for_read(self, model, **hints):
        return 'media' if model._meta.app_label == self.app_label else None

    def db_for_write(self, model, **hints):
        return 'media' if model._meta.app_label == self.app_label else None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == self.app_label:
            return db == 'media'
        return db == 'default'
