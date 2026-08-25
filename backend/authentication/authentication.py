from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Lê o access token do cookie httpOnly em vez do header Authorization."""

    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
