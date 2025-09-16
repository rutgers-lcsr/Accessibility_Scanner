#!/bin/bash
set -e

flask db upgrade
if [ $? -eq 0 ]; then
    echo "Database migrations completed successfully"
else
    echo "Database migrations failed"
    exit 1
fi

python -c "
from app import create_app, init_admin

app = create_app()
init_admin(app)
print(\"Initialization complete\")
"

exec "$@"
