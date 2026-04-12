#!/bin/sh
set -e

echo "[django] Resolving migration state..."

python manage.py shell -c "
from django.db import connection

def table_exists(name):
    with connection.cursor() as c:
        c.execute(
            \"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name=%s)\",
            [name]
        )
        return c.fetchone()[0]

def get_applied(app):
    if not table_exists('django_migrations'):
        return []
    with connection.cursor() as c:
        c.execute(\"SELECT name FROM django_migrations WHERE app=%s ORDER BY name\", [app])
        return [r[0] for r in c.fetchall()]

def set_applied(app, names):
    with connection.cursor() as c:
        c.execute(\"DELETE FROM django_migrations WHERE app=%s\", [app])
        for name in names:
            c.execute(
                \"INSERT INTO django_migrations(app,name,applied) VALUES(%s,%s,NOW())\",
                [app, name]
            )

# The canonical migrations
CANONICAL = ['0001_initial', '0002_submissionprocess_submissionstepdefinition_and_more', '0003_collectionmapping']

applied = get_applied('api')
tables_exist = table_exists('api_entitycluster')

if tables_exist and applied != CANONICAL:
    print(f'[django] Tables exist with records: {applied}')
    print(f'[django] Updating to canonical: {CANONICAL}')
    set_applied('api', CANONICAL)
    print('[django] Migration records updated — no DDL will re-run.')
elif not tables_exist and applied:
    print('[django] Tables missing but records exist — clearing for fresh create.')
    set_applied('api', [])
else:
    print(f'[django] Migration state OK: {applied}')
"

echo "[django] Running migrations..."
python manage.py migrate --noinput

echo "[django] Collecting static files..."
python manage.py collectstatic --noinput --clear 2>/dev/null || true

echo "[django] Loading initial seed data..."
python manage.py shell -c "
from api.models import EntityCluster
if not EntityCluster.objects.exists():
    from django.core.management import call_command
    call_command('loaddata', 'initial_data')
    print('[django] Seed data loaded.')
else:
    print('[django] Seed data already present, skipping.')
"

echo "[django] Importing plain profile config (metadata + submission forms + processes)..."
python manage.py shell -c "
from api.models import MetadataField
import os
if not MetadataField.objects.exists():
    config_dir = os.environ.get('PLAIN_CONFIG_DIR', '/app/frontend-config')
    if os.path.exists(config_dir):
        from django.core.management import call_command
        call_command('import_plain_config', config_dir=config_dir)
        print('[django] Plain config imported.')
    else:
        print(f'[django] Config dir not found: {config_dir}')
        print('[django] Run: python manage.py import_plain_config --config-dir <path>')
else:
    print('[django] Metadata already present, skipping import.')
"

echo "[django] Starting Gunicorn on ${GUNICORN_BIND:-0.0.0.0:5189}..."
exec gunicorn dspace_config.wsgi:application \
    --bind "${GUNICORN_BIND:-0.0.0.0:5189}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout 120 --access-logfile - --error-logfile -
