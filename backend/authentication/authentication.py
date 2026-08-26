from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Lê o access token do cookie httpOnly em vez do header Authorization."""

    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token


class CookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """Descreve CookieJWTAuthentication pro schema OpenAPI — sem isso,
    drf-spectacular não reconhece a classe (não é um scheme padrão) e emite
    warning em toda view autenticada. Documentada como apiKey em cookie
    (não bearer/header), já que é exatamente assim que o token é lido."""

    target_class = 'authentication.authentication.CookieJWTAuthentication'
    name = 'cookieAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'cookie',
            'name': settings.JWT_AUTH_COOKIE,
            'description': 'JWT de acesso enviado via cookie httpOnly (definido em /api/auth/login/).',
        }
