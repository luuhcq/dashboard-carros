from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken


class DetailResponseSerializer(serializers.Serializer):
    """Formato comum de resposta de login/refresh/logout — só uma mensagem;
    os tokens em si nunca aparecem no corpo (Prompt 04), só nos cookies
    httpOnly, que o OpenAPI não descreve como parte do body."""

    detail = serializers.CharField()


class MeResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


def _cookie_kwargs():
    return {
        'httponly': True,
        'secure': settings.JWT_AUTH_COOKIE_SECURE,
        'samesite': settings.JWT_AUTH_COOKIE_SAMESITE,
        'path': '/',
    }


def _set_access_cookie(response, access_token):
    response.set_cookie(
        settings.JWT_AUTH_COOKIE,
        access_token,
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        **_cookie_kwargs(),
    )


def _set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        settings.JWT_AUTH_REFRESH_COOKIE,
        refresh_token,
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        **_cookie_kwargs(),
    )


def _delete_auth_cookies(response):
    response.delete_cookie(settings.JWT_AUTH_COOKIE, path='/')
    response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE, path='/')


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=TokenObtainPairSerializer,
        responses={200: DetailResponseSerializer},
        description=(
            'Autentica com username/password e define access_token/refresh_token '
            'como cookies httpOnly — os tokens nunca aparecem no corpo da resposta.'
        ),
    )
    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access_token = serializer.validated_data['access']
        refresh_token = serializer.validated_data['refresh']

        response = Response({'detail': 'login realizado com sucesso'}, status=status.HTTP_200_OK)
        _set_access_cookie(response, access_token)
        _set_refresh_cookie(response, refresh_token)
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        responses={200: DetailResponseSerializer},
        description=(
            'Renova o access_token a partir do refresh_token lido do cookie httpOnly '
            '(não do corpo da requisição). Rotaciona também o refresh_token.'
        ),
    )
    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        if not refresh_token:
            return Response(
                {'detail': 'refresh token ausente'}, status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return Response(
                {'detail': 'refresh token inválido ou expirado'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access_token = serializer.validated_data['access']
        new_refresh_token = serializer.validated_data.get('refresh')

        response = Response({'detail': 'token renovado'}, status=status.HTTP_200_OK)
        _set_access_cookie(response, access_token)
        if new_refresh_token:
            _set_refresh_cookie(response, new_refresh_token)
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        responses={200: DetailResponseSerializer},
        description=(
            'Invalida (blacklist) o refresh_token do cookie httpOnly e limpa os '
            'cookies de autenticação. Best-effort: cookie ausente ou inválido não '
            'impede o logout de retornar sucesso.'
        ),
    )
    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        response = Response({'detail': 'logout realizado com sucesso'}, status=status.HTTP_200_OK)
        _delete_auth_cookies(response)
        return response


class MeView(APIView):
    @extend_schema(responses={200: MeResponseSerializer})
    def get(self, request):
        return Response(
            {'id': request.user.id, 'username': request.user.username}
        )
