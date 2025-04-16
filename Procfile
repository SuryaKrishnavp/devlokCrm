release: python manage.py makemigrations && python manage.py migrate
web: daphne -b 0.0.0.0 -p $PORT devlok_crm.asgi:application
worker: celery -A devlok_crm worker --loglevel=info
