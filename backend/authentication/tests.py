from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.username = 'revenda'
        self.password = 'S3nhaForte!23'
        self.user = get_user_model().objects.create_user(
            username=self.username, password=self.password
        )
        self.login_url = reverse('auth-login')
        self.refresh_url = reverse('auth-refresh')
        self.logout_url = reverse('auth-logout')
        self.me_url = reverse('auth-me')

    def _login(self):
        return self.client.post(
            self.login_url,
            {'username': self.username, 'password': self.password},
            format='json',
        )

    def test_protected_endpoint_without_cookie_returns_401(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_sets_httponly_cookies_without_exposing_tokens_in_body(self):
        response = self._login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)

        access_cookie = response.cookies[settings.JWT_AUTH_COOKIE]
        refresh_cookie = response.cookies[settings.JWT_AUTH_REFRESH_COOKIE]
        self.assertTrue(access_cookie['httponly'])
        self.assertTrue(refresh_cookie['httponly'])
        self.assertTrue(access_cookie)
        self.assertTrue(refresh_cookie)

    def test_login_then_protected_endpoint_returns_user(self):
        self._login()

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.username)

    def test_wrong_credentials_returns_401_and_no_cookie(self):
        response = self.client.post(
            self.login_url,
            {'username': self.username, 'password': 'senha-errada'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn(settings.JWT_AUTH_COOKIE, response.cookies)

    def test_logout_clears_cookies_and_blacklists_refresh_token(self):
        self._login()

        logout_response = self.client.post(self.logout_url)
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertEqual(logout_response.cookies[settings.JWT_AUTH_COOKIE].value, '')
        self.assertEqual(logout_response.cookies[settings.JWT_AUTH_REFRESH_COOKIE].value, '')

        me_response = self.client.get(self.me_url)
        self.assertEqual(me_response.status_code, status.HTTP_401_UNAUTHORIZED)

        refresh_response = self.client.post(self.refresh_url)
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_issues_new_access_cookie(self):
        login_response = self._login()
        old_access = login_response.cookies[settings.JWT_AUTH_COOKIE].value

        refresh_response = self.client.post(self.refresh_url)

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        new_access = refresh_response.cookies[settings.JWT_AUTH_COOKIE].value
        self.assertTrue(new_access)
        self.assertNotEqual(old_access, new_access)
