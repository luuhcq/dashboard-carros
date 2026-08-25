from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',  # Vite (padrão)
]

# http://localhost não é HTTPS — cookie Secure=True seria recusado pelo navegador.
JWT_AUTH_COOKIE_SECURE = False
