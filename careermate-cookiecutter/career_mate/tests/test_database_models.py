from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.candidates.models import Candidate, Skill
from apps.jobs.models import Application, Job, JobCategory
from apps.recruiters.models import Company, Recruiter
from apps.resume.models import Resume

User = get_user_model()


class DatabaseModelsTestCase(TestCase):
    """
    Tests for PostgreSQL models, relationships, and constraints.
    """

    def setUp(self):
        # 1. Create Users
        self.candidate_user = User.objects.create_user(
            username="candidate_john",
            email="john@example.com",
            password="testpassword123",
            first_name="John",
            last_name="Doe",
        )
        self.recruiter_user = User.objects.create_user(
            username="recruiter_jane",
            email="jane@example.com",
            password="testpassword123",
            first_name="Jane",
            last_name="Smith",
        )

        # 2. Create Skill
        self.skill_python = Skill.objects.create(name="Python", category="Programming")
        self.skill_django = Skill.objects.create(name="Django", category="Framework")

        # 3. Create Candidate Profile
        self.candidate = Candidate.objects.create(
            user=self.candidate_user,
            headline="Full Stack Python Developer",
            phone="+919876543210",
            location="Bangalore, India",
            experience_years=2,
            education="Master of Computer Applications (MCA)",
            profile_complete=True,
        )
        self.candidate.skills.add(self.skill_python, self.skill_django)

        # 4. Create Company & Recruiter
        self.company = Company.objects.create(
            name="TechCorp Solutions",
            description="Leading AI and Web Solutions Provider",
            website="https://techcorp.example.com",
            location="Bangalore, India",
            industry="Information Technology",
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user,
            company=self.company,
            designation="Senior Technical Recruiter",
            phone="+919876543211",
        )

        # 5. Create Job Category & Job
        self.category = JobCategory.objects.create(
            name="Software Engineering",
            description="Software development roles",
        )
        self.job = Job.objects.create(
            title="Backend Django Engineer",
            recruiter=self.recruiter,
            company=self.company,
            category=self.category,
            description="We are looking for a skilled Django developer.",
            requirements="Python, Django, PostgreSQL, Docker",
            location="Bangalore / Remote",
            employment_type="full_time",
            min_experience=2,
            salary_min=600000.00,
            salary_max=1200000.00,
            status="active",
        )
        self.job.skills_required.add(self.skill_python, self.skill_django)

        # 6. Create Resume
        dummy_file = SimpleUploadedFile(
            "john_doe_resume.pdf",
            b"PDF-dummy-content-for-testing",
            content_type="application/pdf",
        )
        self.resume = Resume.objects.create(
            candidate=self.candidate,
            file=dummy_file,
            file_name="john_doe_resume.pdf",
            parsed_text="John Doe Python Django developer experience",
            status="parsed",
        )

        # 7. Create Application
        self.application = Application.objects.create(
            job=self.job,
            candidate=self.candidate,
            resume=self.resume,
            status="applied",
        )

    def test_candidate_creation_and_skills(self):
        self.assertEqual(self.candidate.user.username, "candidate_john")
        self.assertEqual(self.candidate.skills.count(), 2)
        self.assertIn(self.skill_python, self.candidate.skills.all())
        self.assertTrue(self.candidate.profile_complete)

    def test_company_and_recruiter_relationship(self):
        self.assertEqual(self.company.recruiters.count(), 1)
        self.assertEqual(self.recruiter.company, self.company)
        self.assertEqual(str(self.company), "TechCorp Solutions")

    def test_job_and_application_relationship(self):
        self.assertEqual(self.job.applications.count(), 1)
        self.assertEqual(self.job.skills_required.count(), 2)
        self.assertEqual(self.application.candidate, self.candidate)
        self.assertEqual(self.application.resume, self.resume)
        self.assertEqual(self.application.status, "applied")

    def test_unique_application_constraint(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Application.objects.create(
                job=self.job,
                candidate=self.candidate,
                resume=self.resume,
            )

    def test_resume_str_and_status(self):
        self.assertEqual(self.resume.status, "parsed")
        self.assertTrue("john_doe_resume.pdf" in str(self.resume))


class AdminAccessTestCase(TestCase):
    """
    Tests to verify Django Admin interface access.
    """

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin_test",
            email="admintest@careermate.ai",
            password="adminpassword123",
        )

    def test_admin_login_page_renders(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)  # redirects to admin:login

        # Login as superuser
        login_success = self.client.login(username="admin_test", password="adminpassword123")
        self.assertTrue(login_success)

        # Access admin index
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CareerMate AI")
        self.assertContains(response, "Candidates")
        self.assertContains(response, "Companies")
        self.assertContains(response, "Jobs")
        self.assertContains(response, "Applications")
        self.assertContains(response, "Resumes")
