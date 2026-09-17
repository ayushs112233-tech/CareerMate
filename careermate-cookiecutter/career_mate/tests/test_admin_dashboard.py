from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.candidates.models import Candidate, Skill
from apps.jobs.models import Application, Job, JobCategory
from apps.recruiters.models import Company, Recruiter
from apps.resume.models import Resume

User = get_user_model()


class CustomAdminDashboardTestCase(TestCase):
    """
    Automated test suite for CareerMate AI Custom Admin Management Dashboard.
    """

    def setUp(self):
        self.client = Client()

        # 1. Create Staff / Superuser
        self.admin_user = User.objects.create_superuser(
            username="dashboard_admin",
            email="admin@careermate.ai",
            password="adminpassword123",
            first_name="Admin",
            last_name="Super",
        )

        # 2. Create Normal User (non-staff)
        self.normal_user = User.objects.create_user(
            username="normal_candidate",
            email="candidate@example.com",
            password="normalpassword123",
        )

        # 3. Create Sample Seed Data
        self.skill = Skill.objects.create(name="Python", category="Programming")
        self.category = JobCategory.objects.create(name="Software Engineering")
        self.company = Company.objects.create(name="Test Innovations Ltd", location="Bangalore")
        self.recruiter = Recruiter.objects.create(
            user=self.admin_user,
            company=self.company,
            designation="HR Manager",
        )
        self.candidate = Candidate.objects.create(
            user=self.normal_user,
            headline="Junior Python Dev",
            experience_years=1,
            profile_complete=True,
        )
        self.candidate.skills.add(self.skill)

        self.job = Job.objects.create(
            title="Django Developer",
            company=self.company,
            recruiter=self.recruiter,
            category=self.category,
            description="Django backend dev",
            location="Remote",
            status="active",
        )
        self.job.skills_required.add(self.skill)

        self.resume = Resume.objects.create(
            candidate=self.candidate,
            file=SimpleUploadedFile("resume.pdf", b"Dummy PDF bytes"),
            file_name="resume.pdf",
            parsed_text="Python Django Candidate text",
            status="uploaded",
        )

        self.application = Application.objects.create(
            job=self.job,
            candidate=self.candidate,
            resume=self.resume,
            status="applied",
        )

    def test_unauthenticated_access_redirects_to_login(self):
        response = self.client.get(reverse("admin_panel:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_non_staff_user_is_denied(self):
        self.client.login(username="normal_candidate", password="normalpassword123")
        response = self.client.get(reverse("admin_panel:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_staff_login_and_dashboard_renders(self):
        self.client.login(username="dashboard_admin", password="adminpassword123")
        response = self.client.get(reverse("admin_panel:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CareerMate")
        self.assertContains(response, "Total Candidates")
        self.assertEqual(response.context["total_candidates"], 1)
        self.assertEqual(response.context["total_jobs"], 1)
        self.assertEqual(response.context["total_companies"], 1)
        self.assertEqual(response.context["total_applications"], 1)

    def test_all_management_list_views_render(self):
        self.client.login(username="dashboard_admin", password="adminpassword123")
        views_to_test = [
            ("admin_panel:candidates", "Candidate Profiles"),
            ("admin_panel:recruiters", "Recruiter Profiles"),
            ("admin_panel:companies", "Registered Companies"),
            ("admin_panel:jobs", "Job Postings"),
            ("admin_panel:applications", "Job Applications Workflow"),
            ("admin_panel:resumes", "Uploaded Resumes Repository"),
            ("admin_panel:skills", "Skills Catalog Management"),
            ("admin_panel:job_categories", "Job Categories Management"),
            ("admin_panel:reports", "Platform Statistics & Reports"),
        ]

        for url_name, expected_text in views_to_test:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_text)

    def test_detail_views_render(self):
        self.client.login(username="dashboard_admin", password="adminpassword123")

        # Candidate Detail
        resp = self.client.get(reverse("admin_panel:candidate_detail", args=[self.candidate.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Junior Python Dev")

        # Job Detail
        resp = self.client.get(reverse("admin_panel:job_detail", args=[self.job.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Django Developer")

        # Application Detail
        resp = self.client.get(reverse("admin_panel:application_detail", args=[self.application.pk]))
        self.assertEqual(resp.status_code, 200)

        # Resume Detail
        resp = self.client.get(reverse("admin_panel:resume_detail", args=[self.resume.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Python Django Candidate text")

    def test_skill_create_and_delete_workflow(self):
        self.client.login(username="dashboard_admin", password="adminpassword123")

        # Create Skill
        create_resp = self.client.post(
            reverse("admin_panel:skill_create"),
            {"name": "ReactJS", "category": "Frontend Framework"},
            follow=True,
        )
        self.assertEqual(create_resp.status_code, 200)
        self.assertTrue(Skill.objects.filter(name="ReactJS").exists())

        # Delete Skill
        new_skill = Skill.objects.get(name="ReactJS")
        del_resp = self.client.post(reverse("admin_panel:skill_delete", args=[new_skill.pk]), follow=True)
        self.assertEqual(del_resp.status_code, 200)
        self.assertFalse(Skill.objects.filter(name="ReactJS").exists())

    def test_application_status_update_workflow(self):
        self.client.login(username="dashboard_admin", password="adminpassword123")

        update_resp = self.client.post(
            reverse("admin_panel:application_status_update", args=[self.application.pk]),
            {"status": "shortlisted"},
            follow=True,
        )
        self.assertEqual(update_resp.status_code, 200)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "shortlisted")
