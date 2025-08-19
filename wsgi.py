from app import app

if __name__ == "__main__":
    app.run()

# For WSGI servers (e.g., gunicorn, uWSGI), expose 'app'
application = app