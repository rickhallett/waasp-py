"""Celery tasks for async processing."""

from celery import Celery

from waasp.config import get_settings


def make_celery(app=None) -> Celery:
    """Create and configure Celery instance.
    
    Args:
        app: Optional Flask app for context
        
    Returns:
        Configured Celery instance
    """
    settings = get_settings()
    
    celery = Celery(
        "waasp",
        broker=settings.redis_url,
        backend=settings.celery_result_backend,
    )
    
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )
    
    if app:
        celery.conf.update(app.config)
        
        class ContextTask(celery.Task):
            """Task that runs within Flask app context."""
            
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery


celery_app = make_celery()
