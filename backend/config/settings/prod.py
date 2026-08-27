from .base import *  # noqa: F401,F403

DEBUG = False

if not ALLOWED_HOSTS:  # noqa: F405
    raise ValueError('ALLOWED_HOSTS precisa estar definido via .env em produção.')

# CORS_ALLOW_CREDENTIALS = True vale globalmente (base.py) por causa do cookie JWT
# httpOnly — uma origem coringa ou lista vazia aqui não é auto-corrigível pelo
# django-cors-headers (não há CORS_ALLOW_ALL_ORIGINS configurado), mas falhar
# alto no boot é mais seguro do que descobrir em runtime que o front não conecta
# ou, pior, que alguém adicionou um "*" pensando que funciona como ALLOWED_HOSTS.
if not CORS_ALLOWED_ORIGINS or '*' in CORS_ALLOWED_ORIGINS:  # noqa: F405
    raise ValueError(
        'CORS_ALLOWED_ORIGINS precisa ser uma lista fechada de domínios reais via '
        '.env em produção — não pode ser vazia nem conter "*".'
    )

SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

JWT_AUTH_COOKIE_SECURE = True
