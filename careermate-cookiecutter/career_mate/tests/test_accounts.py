from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthenticationTests(TestCase):
    def registration_data(self, **overrides):
        data = {
            "username": "albin",
            "email": "albin@example.com",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
        }
        data.update(overrides)
        return data

    def test_home_redirects_to_login(self):
        response = self.client.get("/")

        self.assertRedirects(response, reverse("accounts:login"))

    def test_user_can_register_with_hashed_password(self):
        response = self.client.post(reverse("accounts:register"), self.registration_data())

        self.assertRedirects(response, reverse("accounts:login"))
        user = User.objects.get(username="albin")
        self.assertTrue(user.check_password("StrongPassword123!"))

    def test_duplicate_email_registration_is_rejected(self):
        User.objects.create_user("existing", "albin@example.com", "StrongPassword123!")

        response = self.client.post(reverse("accounts:register"), self.registration_data())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(User.objects.count(), 1)

    def test_password_confirmation_is_validated(self):
        response = self.client.post(
            reverse("accounts:register"), self.registration_data(password2="DifferentPassword123!")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)

    def test_login_creates_an_authenticated_session(self):
        User.objects.create_user("albin", "albin@example.com", "StrongPassword123!")

        response = self.client.post(
            reverse("accounts:login"), {"username": "albin", "password": "StrongPassword123!"}
        )

        self.assertRedirects(response, reverse("accounts:login"))
        response = self.client.get(reverse("accounts:login"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_invalid_login_does_not_authenticate(self):
        User.objects.create_user("albin", "albin@example.com", "StrongPassword123!")

        response = self.client.post(
            reverse("accounts:login"), {"username": "albin", "password": "incorrect"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_ends_the_session(self):
        user = User.objects.create_user("albin", "albin@example.com", "StrongPassword123!")
        self.client.force_login(user)

        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("accounts:login"))
        response = self.client.get(reverse("accounts:login"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)
