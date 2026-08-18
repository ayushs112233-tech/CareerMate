from django.test import TestCase
from django.urls import reverse


class CandidateUiTests(TestCase):
    def test_candidate_pages_render(self):
        pages = [
            "candidate_dashboard",
            "candidate_profile",
            "candidate_resume",
            "candidate_jobs",
            "candidate_ats_score",
            "candidate_career_path",
        ]

        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(reverse(f"candidate:{page}"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "CareerMate AI")
