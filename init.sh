#!/bin/bash
set -e

python -c "
from app import create_app, init_admin

app = create_app()
init_admin(app)
print(\"Initialization complete\")
"

exec "$@"
