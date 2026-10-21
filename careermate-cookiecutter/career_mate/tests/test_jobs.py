import os
import shutil
import tempfile
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.candidates.models import Candidate, Skill
from apps.jobs.models import Application, Job, JobCategory
from apps.recruiters.models import Company, Recruiter
from apps.resume.models import Resume

User = get_user_model()


class RecruiterResumeFeatureTestCase(TestCase):
    """
    Test suite verifying recruiter resume viewing, downloading,
    authorization boundaries, error handling, and applicant management.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_media = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(cls.temp_media, ignore_errors=True)

    def setUp(self):
        # Apply media root override
        self._media_override = override_settings(MEDIA_ROOT=self.temp_media)
        self._media_override.enable()

        # 1. Create Candidate 1
        self.cand1_user = User.objects.create_user(
            username="candidate_alice",
            email="alice@example.com",
            password="password123",
            first_name="Alice",
            last_name="Johnson",
        )
        self.cand1 = Candidate.objects.create(
            user=self.cand1_user,
            headline="Full Stack Python Engineer",
            profile_complete=True,
        )

        # 2. Create Candidate 2
        self.cand2_user = User.objects.create_user(
            username="candidate_bob",
            email="bob@example.com",
            password="password123",
            first_name="Bob",
            last_name="Smith",
        )
        self.cand2 = Candidate.objects.create(
            user=self.cand2_user,
            headline="Data Analyst",
            profile_complete=True,
        )

        # 3. Create Recruiter 1
        self.rec1_user = User.objects.create_user(
            username="recruiter_carol",
            email="carol@techcorp.com",
            password="password123",
            first_name="Carol",
            last_name="Danvers",
        )
        self.comp1 = Company.objects.create(name="TechCorp AI")
        self.rec1 = Recruiter.objects.create(
            user=self.rec1_user,
            company=self.comp1,
            designation="Talent Lead",
        )

        # 4. Create Recruiter 2 (Separate recruiter)
        self.rec2_user = User.objects.create_user(
            username="recruiter_dave",
            email="dave@innovate.com",
            password="password123",
            first_name="Dave",
            last_name="Miller",
        )
        self.comp2 = Company.objects.create(name="Innovate Ltd")
        self.rec2 = Recruiter.objects.create(
            user=self.rec2_user,
            company=self.comp2,
            designation="HR Manager",
        )

        # 5. Job Category
        self.category = JobCategory.objects.create(name="Engineering")

        # 6. Jobs
        self.job1 = Job.objects.create(
            title="Senior Django Developer",
            recruiter=self.rec1,
            company=self.comp1,
            category=self.category,
            description="Build scalable web platforms.",
            status="active",
        )
        self.job2 = Job.objects.create(
            title="Product Designer",
            recruiter=self.rec2,
            company=self.comp2,
            category=self.category,
            description="Design intuitive UI.",
            status="active",
        )
        self.job_empty = Job.objects.create(
            title="DevOps Specialist",
            recruiter=self.rec1,
            company=self.comp1,
            category=self.category,
            description="Maintain CI/CD pipelines.",
            status="active",
        )

        # 7. Resumes
        pdf_file1 = SimpleUploadedFile(
            "alice_resume.pdf",
            b"%PDF-1.4 test resume content for Alice Johnson",
            content_type="application/pdf",
        )
        self.resume1 = Resume.objects.create(
            candidate=self.cand1,
            file=pdf_file1,
            file_name="alice_resume.pdf",
            parsed_text="Alice Johnson Python Django AWS",
            status="parsed",
        )

        pdf_file2 = SimpleUploadedFile(
            "bob_resume.pdf",
            b"%PDF-1.4 test resume content for Bob Smith",
            content_type="application/pdf",
        )
        self.resume2 = Resume.objects.create(
            candidate=self.cand2,
            file=pdf_file2,
            file_name="bob_resume.pdf",
            parsed_text="Bob Smith SQL Python Tableau",
            status="parsed",
        )

        # 8. Applications
        # Application 1: Alice -> Job 1 (Owned by Recruiter 1) with resume1
        self.app1 = Application.objects.create(
            job=self.job1,
            candidate=self.cand1,
            resume=self.resume1,
            status="applied",
        )

        # Application 2: Bob -> Job 2 (Owned by Recruiter 2) with resume2
        self.app2 = Application.objects.create(
            job=self.job2,
            candidate=self.cand2,
            resume=self.resume2,
            status="applied",
        )

        # Application 3: Bob -> Job 1 (Owned by Recruiter 1) WITHOUT resume
        self.app_no_resume = Application.objects.create(
            job=self.job1,
            candidate=self.cand2,
            resume=None,
            status="applied",
        )

    def tearDown(self):
        self._media_override.disable()

    # --- Test 1: Candidate applies for a job with resume ---
    def test_candidate_job_application_associates_latest_resume(self):
        """When a candidate applies for an active job, their latest resume is attached."""
        client = Client()
        client.login(username="candidate_alice", password="password123")
        
        # Candidate 1 applies for Job 2
        response = client.post(reverse("candidate_job_detail", kwargs={"pk": self.job2.pk}))
        self.assertEqual(response.status_code, 302)
        
        new_app = Application.objects.filter(job=self.job2, candidate=self.cand1).first()
        self.assertIsNotNone(new_app)
        self.assertEqual(new_app.resume, self.resume1)
        self.assertTrue(new_app.has_resume_file)

    # --- Test 2: Recruiter can view applicant resume inline ---
    def test_recruiter_can_view_applicant_resume_inline(self):
        """Recruiter who owns the job can view the applicant's resume inline in browser."""
        client = Client()
        client.login(username="recruiter_carol", password="password123")

        url = reverse("jobs:application_resume_view", kwargs={"pk": self.app1.pk})
        response = client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        content_disp = response.headers.get("Content-Disposition", "")
        # Inline response should not specify attachment
        self.assertNotIn("attachment", content_disp.lower())
        self.assertIn("inline", content_disp.lower())
        self.assertIn(b"%PDF-1.4 test resume content for Alice Johnson", response.getvalue())

    # --- Test 3: Recruiter can download applicant resume ---
    def test_recruiter_can_download_applicant_resume(self):
        """Recruiter who owns the job can download the applicant's resume as attachment."""
        client = Client()
        client.login(username="recruiter_carol", password="password123")

        url = reverse("jobs:application_resume_download", kwargs={"pk": self.app1.pk})
        response = client.get(url)

        self.assertEqual(response.status_code, 200)
        content_disp = response.headers.get("Content-Disposition", "")
        self.assertIn("attachment", content_disp.lower())
        self.assertIn("alice_resume.pdf", content_disp)
        self.assertIn(b"%PDF-1.4 test resume content for Alice Johnson", response.getvalue())

    # --- Test 4: Recruiter cannot access another recruiter's applicant resume ---
    def test_recruiter_cannot_access_other_recruiters_applicant_resume(self):
        """Recruiter 2 cannot view or download resumes for Recruiter 1's applicants."""
        client = Client()
        client.login(username="recruiter_dave", password="password123")

        # Dave tries to access Carol's applicant (app1)
        view_url = reverse("jobs:application_resume_view", kwargs={"pk": self.app1.pk})
        download_url = reverse("jobs:application_resume_download", kwargs={"pk": self.app1.pk})

        resp_view = client.get(view_url)
        self.assertEqual(resp_view.status_code, 404)

        resp_download = client.get(download_url)
        self.assertEqual(resp_download.status_code, 404)

    # --- Test 5: Unauthenticated users are redirected to login ---
    def test_unauthenticated_user_cannot_access_resumes(self):
        """Unauthenticated requests are securely redirected to the login page."""
        client = Client()
        view_url = reverse("jobs:application_resume_view", kwargs={"pk": self.app1.pk})
        download_url = reverse("jobs:application_resume_download", kwargs={"pk": self.app1.pk})

        resp_view = client.get(view_url)
        self.assertEqual(resp_view.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp_view.url)

        resp_download = client.get(download_url)
        self.assertEqual(resp_download.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp_download.url)

    # --- Test 6: Candidates cannot access recruiter resume endpoints ---
    def test_candidate_cannot_access_recruiter_resume_endpoint(self):
        """Candidates accessing recruiter resume endpoints are denied access (HTTP 403)."""
        client = Client()
        client.login(username="candidate_alice", password="password123")

        view_url = reverse("jobs:application_resume_view", kwargs={"pk": self.app1.pk})
        download_url = reverse("jobs:application_resume_download", kwargs={"pk": self.app1.pk})

        resp_view = client.get(view_url)
        self.assertEqual(resp_view.status_code, 403)

        resp_download = client.get(download_url)
        self.assertEqual(resp_download.status_code, 403)

    # --- Test 7: Candidate cannot download other candidates' resumes via candidate endpoint ---
    def test_candidate_cannot_download_other_candidates_resume(self):
        """Candidate Alice cannot download Candidate Bob's resume via candidate download endpoint."""
        client = Client()
        client.login(username="candidate_alice", password="password123")

        url = reverse("candidate_resume_download", kwargs={"pk": self.resume2.pk})
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    # --- Test 8: Application without resume handled gracefully ---
    def test_application_without_resume_handled_gracefully(self):
        """Accessing resume for an application without resume returns 404 without crashing."""
        client = Client()
        client.login(username="recruiter_carol", password="password123")

        view_url = reverse("jobs:application_resume_view", kwargs={"pk": self.app_no_resume.pk})
        download_url = reverse("jobs:application_resume_download", kwargs={"pk": self.app_no_resume.pk})

        resp_view = client.get(view_url)
        self.assertEqual(resp_view.status_code, 404)

        resp_download = client.get(download_url)
        self.assertEqual(resp_download.status_code, 404)

    # --- Test 9: Deleted or missing physical file handled gracefully ---
    def test_deleted_or_missing_file_handled_gracefully(self):
        """When the physical file is missing from storage, returns 404 instead of 500."""
        job_ghost = Job.objects.create(
            title="Cloud Architect",
            recruiter=self.rec1,
            company=self.comp1,
            category=self.category,
            description="Cloud role.",
            status="active",
        )
        ghost_resume = Resume.objects.create(
            candidate=self.cand1,
            file_name="deleted_file.pdf",
            parsed_text="Sample",
            status="parsed",
        )
        ghost_resume.file.name = "resumes/2026/10/ghost_file_missing.pdf"
        ghost_resume.save()

        ghost_app = Application.objects.create(
            job=job_ghost,
            candidate=self.cand1,
            resume=ghost_resume,
            status="applied",
        )

        client = Client()
        client.login(username="recruiter_carol", password="password123")

        view_url = reverse("jobs:application_resume_view", kwargs={"pk": ghost_app.pk})
        download_url = reverse("jobs:application_resume_download", kwargs={"pk": ghost_app.pk})

        resp_view = client.get(view_url)
        self.assertEqual(resp_view.status_code, 404)

        resp_download = client.get(download_url)
        self.assertEqual(resp_download.status_code, 404)

    # --- Test 10: Invalid application IDs rejected safely ---
    def test_invalid_application_id_rejected(self):
        """Non-existent application IDs return 404 safely."""
        client = Client()
        client.login(username="recruiter_carol", password="password123")

        view_url = reverse("jobs:application_resume_view", kwargs={"pk": 999999})
        download_url = reverse("jobs:application_resume_download", kwargs={"pk": 999999})

        self.assertEqual(client.get(view_url).status_code, 404)
        self.assertEqual(client.get(download_url).status_code, 404)

    # --- Test 11: Recruiter applications page UI elements ---
    def test_recruiter_applications_page_displays_resume_links(self):
        """Applicant management page displays candidate details, View Resume, and Download Resume buttons."""
        client = Client()
        client.login(username="recruiter_carol", password="password123")

        response = client.get(reverse("jobs:recruiter_applications"))
        self.assertEqual(response.status_code, 200)

        # Check for candidate names
        self.assertContains(response, "Alice Johnson")
        self.assertContains(response, "Senior Django Developer")

        # Check for View and Download Resume buttons
        self.assertContains(response, "View Resume")
        self.assertContains(response, "Download Resume")
        self.assertContains(response, reverse("jobs:application_resume_view", kwargs={"pk": self.app1.pk}))
        self.assertContains(response, reverse("jobs:application_resume_download", kwargs={"pk": self.app1.pk}))

        # Check that application without resume shows "No Resume"
        self.assertContains(response, "No Resume")

    # --- Test 12: Recruiter job detail page displays applicants & resume buttons ---
    def test_recruiter_job_detail_page_displays_applicants(self):
        """Job detail page lists applicants for the role with View and Download Resume actions."""
        client = Client()
        client.login(username="recruiter_carol", password="password123")

        response = client.get(reverse("jobs:recruiter_detail", kwargs={"pk": self.job1.pk}))
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Applicants for this Role")
        self.assertContains(response, "Alice Johnson")
        self.assertContains(response, "View Resume")
        self.assertContains(response, "Download Resume")

    # --- Test 13: Job detail page empty state message ---
    def test_recruiter_job_detail_page_empty_applicants(self):
        """When no applicants exist for a job, displays a helpful empty message."""
        client = Client()
        client.login(username="recruiter_carol", password="password123")

        response = client.get(reverse("jobs:recruiter_detail", kwargs={"pk": self.job_empty.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No candidates have applied for this job yet.")

    # --- Test 14: DOCX file format support ---
    def test_docx_resume_handling(self):
        """DOCX files are served with the correct Word document MIME type."""
        job_docx = Job.objects.create(
            title="Technical Writer",
            recruiter=self.rec1,
            company=self.comp1,
            category=self.category,
            description="Documentation role.",
            status="active",
        )
        docx_file = SimpleUploadedFile(
            "alice_resume.docx",
            b"PK\x03\x04 mock docx file content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        docx_resume = Resume.objects.create(
            candidate=self.cand1,
            file=docx_file,
            file_name="alice_resume.docx",
            status="parsed",
        )
        docx_app = Application.objects.create(
            job=job_docx,
            candidate=self.cand1,
            resume=docx_resume,
            status="applied",
        )

        client = Client()
        client.login(username="recruiter_carol", password="password123")

        url = reverse("jobs:application_resume_download", kwargs={"pk": docx_app.pk})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument.wordprocessingml.document", response["Content-Type"])
        self.assertIn("alice_resume.docx", response.headers.get("Content-Disposition", ""))
