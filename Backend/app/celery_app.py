from celery import Celery, Task

def make_celery(app=None):
    """
    Creates and configures a Celery instance tied to the Flask app context.
    """
    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            if app:
                with app.app_context():
                    return self.run(*args, **kwargs)
            return self.run(*args, **kwargs)

    celery_instance = Celery(
        app.import_name if app else "inventory_tasks",
        task_cls=FlaskTask
    )

    if app:
        celery_instance.conf.update(
            broker_url=app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
            result_backend=app.config.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
            task_always_eager=app.config.get("CELERY_TASK_ALWAYS_EAGER", False),
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC"
        )

    return celery_instance

# Global celery instance placeholder
celery = make_celery()