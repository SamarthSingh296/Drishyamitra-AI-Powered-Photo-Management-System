from celery import Celery
from config import Config

def make_celery(app_name=__name__):
    celery = Celery(
        app_name,
        broker=Config.CELERY_BROKER_URL,
        backend=Config.CELERY_RESULT_BACKEND,
        include=['services.tasks']
    )
    celery.conf.update({
        'task_serializer': 'json',
        'result_serializer': 'json',
        'accept_content': ['json'],
        'beat_schedule': {
            'cleanup-temp-storage-daily': {
                'task': 'services.tasks.cleanup_temp_storage',
                'schedule': 86400.0, # Run every 24 hours
            },
        }
    })
    return celery

celery = make_celery()
