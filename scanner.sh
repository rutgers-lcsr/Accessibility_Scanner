#!/bin/bash
set -e

python -c "
from app import create_app, init_scanner

app = create_app()
init_scanner()
print(\"Initialization complete\")
"

