#!/bin/bash

# Wait for the database to be ready
echo "Waiting for database to be ready..."
python << END
import time
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

max_retries = 30
retries = 0

while retries < max_retries:
	try:
		engine = create_engine('${DATABASE_URL}')
		engine.connect()
		print("Database is ready!")
		break
	except OperationalError:
		retries += 1
		print(f"Waiting for database... ({retries}/{max_retries})")
		time.sleep(2)
	except Exception as e:
		print(f"Error: {e}")
		exit(1)

if retries >= max_retries:
	print("Could not connect to database")
	exit(1)
END

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Check if migrations were successful
if [ $? -eq 0 ]; then
	echo "Database migrations completed successfully"
	exit 0
else
	echo "Database migrations failed"
	exit 1
fi