from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from apps.candidates.models import Candidate
from apps.recruiters.models import Recruiter


class AuthenticationTests(TestCase):
    def candidate_registration_data(self, **overrides):
        data = {
            "username": "candidate_albin",
            "first_name": "Albin",
            "last_name": "Thomas",
            "email": "albin@example.com",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
            "headline": "Software Engineer"
        }
        data.update(overrides)
        return data

    def recruiter_registration_data(self, **overrides):
        data = {
            "username": "recruiter_megha",
            "first_name": "Megha",
            "last_name": "Tech",
            "email": "megha@example.com",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
            "company_name": "Megha Corp",
            "designation": "HR"
        }
        data.update(overrides)
        return data

    def test_home_redirects_to_login(self):
        response = self.client.get("/")
        self.assertRedirects(response, reverse("accounts:login"))

    def test_user_can_register_as_candidate(self):
        response = self.client.post(reverse("accounts:register_candidate"), self.candidate_registration_data())
        self.assertRedirects(response, reverse("candidate_dashboard"))
        user = User.objects.get(username="candidate_albin")
        self.assertTrue(user.check_password("StrongPassword123!"))
        self.assertTrue(hasattr(user, "candidate_profile"))
        self.assertEqual(user.candidate_profile.headline, "Software Engineer")

    def test_user_can_register_as_recruiter(self):
        response = self.client.post(reverse("accounts:register_recruiter"), self.recruiter_registration_data())
        self.assertRedirects(response, reverse("recruiters:dashboard"))
        user = User.objects.get(username="recruiter_megha")
        self.assertTrue(hasattr(user, "recruiter_profile"))
        self.assertEqual(user.recruiter_profile.company.name, "Megha Corp")

    def test_duplicate_email_registration_is_rejected(self):
        User.objects.create_user("existing", "albin@example.com", "StrongPassword123!")
        response = self.client.post(reverse("accounts:register_candidate"), self.candidate_registration_data())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(User.objects.count(), 1)

    def test_login_creates_an_authenticated_session(self):
        user = User.objects.create_user("albin", "albin@example.com", "StrongPassword123!")
        Candidate.objects.create(user=user)
        
        response = self.client.post(
            reverse("accounts:login"), {"username": "albin", "password": "StrongPassword123!"}
        )
        self.assertRedirects(response, reverse("candidate_dashboard"))

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

    def test_candidate_cannot_access_recruiter_dashboard(self):
        user = User.objects.create_user("candidate", "candidate@example.com", "pass")
        Candidate.objects.create(user=user)
        self.client.force_login(user)
        response = self.client.get(reverse("recruiters:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_recruiter_cannot_access_candidate_dashboard(self):
        user = User.objects.create_user("recruiter", "recruiter@example.com", "pass")
        Recruiter.objects.create(user=user)
        self.client.force_login(user)
        response = self.client.get(reverse("candidate_dashboard"))
        self.assertEqual(response.status_code, 403)
