from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.candidates.models import Candidate, Skill
from apps.jobs.models import Application, Job, JobCategory
from apps.recruiters.models import Company, Recruiter
from apps.resume.models import Resume
from apps.ai_engine.ats_scorer import calculate_ats_score, generate_resume_suggestions
from apps.ai_engine.resume_comparison import compare_resume_versions, get_candidate_version_history
from apps.ai_engine.job_matching import (
    get_active_analyzed_resume,
    get_candidate_matching_status,
    calculate_hybrid_match_score,
    get_cached_job_match,
    invalidate_candidate_match_cache,
    calculate_job_matches,
)

User = get_user_model()


class ResumeVersionComparisonTestCase(TestCase):
    """
    Comprehensive test suite for Resume Progress & Version Comparison:
    - Sequential version numbering
    - File preservation and independence
    - Historical snapshot immutability
    - Point-difference ATS comparison
    - Skills detection delta (added, retained, dropped)
    - Verifiable suggestion tracking
    - Failure resilience (failed analysis preserves document & past history)
    - Authorization & security (no cross-candidate access)
    - Application resume immutability for recruiters
    """

    def setUp(self):
        # 1. Candidate 1
        self.user1 = User.objects.create_user(
            username="candidate_alice",
            email="alice@example.com",
            password="testpassword123",
        )
        self.candidate1 = Candidate.objects.create(
            user=self.user1,
            headline="Backend Python Developer",
            location="Remote",
            experience_years=3,
        )

        # 2. Candidate 2 (for authorization tests)
        self.user2 = User.objects.create_user(
            username="candidate_bob",
            email="bob@example.com",
            password="testpassword123",
        )
        self.candidate2 = Candidate.objects.create(
            user=self.user2,
            headline="Frontend React Developer",
            location="New York",
            experience_years=2,
        )

        # 3. Recruiter & Company
        self.recruiter_user = User.objects.create_user(
            username="recruiter_carol",
            email="carol@example.com",
            password="testpassword123",
        )
        self.company = Company.objects.create(
            name="Apex Technologies",
            description="Software Engineering Agency",
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user,
            company=self.company,
        )

        # 4. Skills
        self.skill_python = Skill.objects.create(name="Python", category="Backend")
        self.skill_django = Skill.objects.create(name="Django", category="Framework")
        self.skill_docker = Skill.objects.create(name="Docker", category="DevOps")
        self.skill_react = Skill.objects.create(name="React", category="Frontend")
        self.skill_sql = Skill.objects.create(name="SQL", category="Database")

        # Clients
        self.client1 = Client()
        self.client1.force_login(self.user1)

        self.client2 = Client()
        self.client2.force_login(self.user2)

    def test_scenario_1_and_5_sequential_version_numbering(self):
        """1. First upload creates Version 1; 2. Second creates Version 2; 5. Third creates Version 3."""
        r1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v1.pdf", b"%PDF-1.4 dummy 1"),
            file_name="alice_v1.pdf",
            version_number=1,
            status="parsed",
            ats_score=58,
        )
        self.assertEqual(r1.version_number, 1)

        r2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v2.pdf", b"%PDF-1.4 dummy 2"),
            file_name="alice_v2.pdf",
            version_number=2,
            status="parsed",
            ats_score=76,
        )
        self.assertEqual(r2.version_number, 2)

        r3 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v3.pdf", b"%PDF-1.4 dummy 3"),
            file_name="alice_v3.pdf",
            version_number=3,
            status="parsed",
            ats_score=84,
        )
        self.assertEqual(r3.version_number, 3)

        versions = list(self.candidate1.resumes.values_list("version_number", flat=True))
        self.assertEqual(versions, [3, 2, 1])

    def test_scenario_2_and_3_both_versions_retain_original_files(self):
        """Both versions retain their own independent files without overwriting."""
        file1_content = b"%PDF-1.4 Original File 1 Content"
        file2_content = b"%PDF-1.4 Updated File 2 Content"

        r1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("resume_v1.pdf", file1_content),
            file_name="resume_v1.pdf",
            version_number=1,
        )
        r2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("resume_v2.pdf", file2_content),
            file_name="resume_v2.pdf",
            version_number=2,
        )

        self.assertNotEqual(r1.file.name, r2.file.name)
        # Check files exist on storage
        self.assertTrue(r1.file_exists)
        self.assertTrue(r2.file_exists)

    def test_scenario_4_and_6_historical_scores_and_snapshots_immutable(self):
        """Historical ATS scores and extracted text remain unchanged when new resumes are uploaded."""
        v1_text = "Alice Developer. Experience: Python, Django. Education: MCA."
        v1_analysis = {
            "score": 58,
            "breakdown": [{"category": "Skills", "score": 60, "message": "Good"}],
            "extracted_skills": ["Python", "Django"],
            "suggestions": [{"id": "s1", "title": "Add Docker", "category": "keywords"}],
        }
        r1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v1.pdf", b"pdf1"),
            file_name="v1.pdf",
            version_number=1,
            parsed_text=v1_text,
            ats_score=58,
            analysis_data=v1_analysis,
        )

        # Candidate uploads Version 2 with higher score and different text
        v2_text = "Alice Senior Developer. Experience: Python, Django, Docker, SQL. Education: MCA."
        v2_analysis = {
            "score": 82,
            "breakdown": [{"category": "Skills", "score": 90, "message": "Strong"}],
            "extracted_skills": ["Python", "Django", "Docker", "SQL"],
            "suggestions": [],
        }
        r2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v2.pdf", b"pdf2"),
            file_name="v2.pdf",
            version_number=2,
            parsed_text=v2_text,
            ats_score=82,
            analysis_data=v2_analysis,
        )

        # Refresh r1 from DB
        r1.refresh_from_db()
        self.assertEqual(r1.ats_score, 58)
        self.assertEqual(r1.parsed_text, v1_text)
        self.assertEqual(r1.analysis_data["score"], 58)
        self.assertEqual(r1.analysis_data["extracted_skills"], ["Python", "Django"])

    def test_scenario_7_ats_score_point_difference(self):
        """Score change = Latest - Previous (point difference, not percentage)."""
        r1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v1.pdf", b"pdf1"),
            version_number=1,
            ats_score=58,
            analysis_data={"score": 58, "breakdown": [], "extracted_skills": [], "suggestions": []},
        )
        r2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v2.pdf", b"pdf2"),
            version_number=2,
            ats_score=76,
            analysis_data={"score": 76, "breakdown": [], "extracted_skills": [], "suggestions": []},
        )

        comparison = compare_resume_versions(r1, r2)
        self.assertEqual(comparison["point_difference"], 18)
        self.assertEqual(comparison["trend"], "improvement")
        self.assertEqual(comparison["difference_display"], "+18 pts")

        # Test score drop
        r3 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v3.pdf", b"pdf3"),
            version_number=3,
            ats_score=70,
            analysis_data={"score": 70, "breakdown": [], "extracted_skills": [], "suggestions": []},
        )
        drop_comp = compare_resume_versions(r2, r3)
        self.assertEqual(drop_comp["point_difference"], -6)
        self.assertEqual(drop_comp["trend"], "decline")
        self.assertEqual(drop_comp["difference_display"], "-6 pts")

    def test_scenario_8_first_time_upload_no_history_message(self):
        """First time upload shows baseline without false comparisons."""
        r1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v1.pdf", b"pdf1"),
            version_number=1,
            ats_score=65,
            status="parsed",
            analysis_data={"score": 65, "breakdown": []},
        )
        response = self.client1.get(reverse("candidate_resume_progress"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Baseline Version")
        self.assertContains(response, "Comparison Awaiting Next Upload")
        self.assertNotContains(response, "+0 pts")

    def test_scenario_9_skills_comparison(self):
        """Skills comparison identifies added, retained, and dropped skills."""
        r1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v1.pdf", b"pdf1"),
            version_number=1,
            ats_score=50,
            analysis_data={
                "score": 50,
                "extracted_skills": ["Python", "Django", "SQL"],
            },
        )
        r2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v2.pdf", b"pdf2"),
            version_number=2,
            ats_score=75,
            analysis_data={
                "score": 75,
                "extracted_skills": ["Python", "Django", "Docker", "React"],
            },
        )

        comparison = compare_resume_versions(r1, r2)
        skills = comparison["skills"]

        # Added: Docker, React
        self.assertIn("Docker", skills["added"])
        self.assertIn("React", skills["added"])
        self.assertEqual(skills["added_count"], 2)

        # Retained: Python, Django
        self.assertIn("Python", skills["retained"])
        self.assertIn("Django", skills["retained"])
        self.assertEqual(skills["retained_count"], 2)

        # Dropped: SQL
        self.assertIn("SQL", skills["dropped"])
        self.assertEqual(skills["dropped_count"], 1)

    def test_scenario_10_verifiable_suggestion_tracking(self):
        """Suggestions are verified against content and ATS criteria, not falsely marked resolved."""
        # V1 had missing 'experience' section suggestion
        s1 = {
            "id": "missing_experience",
            "category": "sections",
            "title": "Add an 'Experience' or 'Work History' section",
            "description": "Recruiters and ATS parsers look for standard work history headers.",
        }
        r1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v1.pdf", b"pdf1"),
            version_number=1,
            parsed_text="Alice Student. Skills: Python.",
            ats_score=40,
            analysis_data={
                "score": 40,
                "suggestions": [s1],
                "extracted_skills": ["Python"],
                "word_count": 50,
            },
        )

        # Case A: V2 includes "Work Experience: Software Developer at XYZ" -> verified addressed!
        r2_addressed = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v2.pdf", b"pdf2"),
            version_number=2,
            parsed_text="Alice Developer. Experience: Software Developer at XYZ for 2 years. Skills: Python, Django.",
            ats_score=75,
            analysis_data={
                "score": 75,
                "suggestions": [],
                "extracted_skills": ["Python", "Django"],
                "word_count": 280,
            },
        )
        comp_a = compare_resume_versions(r1, r2_addressed)
        addressed_ids = [item["suggestion"]["id"] for item in comp_a["suggestions"]["addressed"]]
        self.assertIn("missing_experience", addressed_ids)

        # Case B: V2 still lacks experience section -> still relevant!
        r2_unaddressed = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v2_alt.pdf", b"pdf2"),
            version_number=3,
            parsed_text="Alice Student. Projects: Personal Blog. Skills: Python, HTML.",
            ats_score=45,
            analysis_data={
                "score": 45,
                "suggestions": [s1],
                "extracted_skills": ["Python"],
                "word_count": 60,
            },
        )
        comp_b = compare_resume_versions(r1, r2_unaddressed)
        still_relevant_ids = [item["suggestion"]["id"] for item in comp_b["suggestions"]["still_relevant"]]
        self.assertIn("missing_experience", still_relevant_ids)

    @patch("apps.candidates.views.extract_text")
    def test_scenario_11_failed_analysis_preserves_historical_data(self, mock_extract):
        """Failed analysis marks status='error' and preserves existing versions without data loss."""
        # Baseline V1
        r1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v1.pdf", b"pdf1"),
            version_number=1,
            ats_score=60,
            status="parsed",
            analysis_data={"score": 60},
        )

        # Mock parser failure
        mock_extract.side_effect = Exception("Corrupt PDF stream")

        upload_file = SimpleUploadedFile("broken.pdf", b"corrupted file content", content_type="application/pdf")
        response = self.client1.post(reverse("candidate_resume"), {"file": upload_file})
        self.assertEqual(response.status_code, 302)

        # Check that V2 was recorded with status='error'
        r2 = Resume.objects.filter(candidate=self.candidate1, version_number=2).first()
        self.assertIsNotNone(r2)
        self.assertEqual(r2.status, "error")

        # Confirm V1 is untouched
        r1.refresh_from_db()
        self.assertEqual(r1.status, "parsed")
        self.assertEqual(r1.ats_score, 60)

    def test_scenario_12_unauthorized_users_cannot_access_other_versions(self):
        """Candidate B cannot view or download Candidate A's resume version."""
        r1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_secret.pdf", b"Alice's confidential resume"),
            version_number=1,
            ats_score=80,
            parsed_text="Confidential data",
            analysis_data={"score": 80},
        )

        # Bob (candidate 2) tries to access Alice's version analysis
        detail_url = reverse("candidate_resume_version_detail", kwargs={"pk": r1.pk})
        resp_detail = self.client2.get(detail_url)
        self.assertEqual(resp_detail.status_code, 404)

        # Bob tries to download Alice's resume file
        download_url = reverse("candidate_resume_download", kwargs={"pk": r1.pk})
        resp_download = self.client2.get(download_url)
        self.assertEqual(resp_download.status_code, 404)

        # Alice herself can access both
        resp_alice_detail = self.client1.get(detail_url)
        self.assertEqual(resp_alice_detail.status_code, 200)

    def test_scenario_13_job_application_resume_version_preservation(self):
        """Job application keeps reference to the specific version submitted even when candidate uploads v2."""
        category = JobCategory.objects.create(name="Engineering")
        job = Job.objects.create(
            company=self.company,
            recruiter=self.recruiter,
            title="Senior Python Engineer",
            category=category,
            status="active",
        )

        r1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v1.pdf", b"Version 1 resume for job app"),
            version_number=1,
            status="parsed",
            ats_score=65,
        )

        # Alice applies for job with V1
        application = Application.objects.create(
            job=job,
            candidate=self.candidate1,
            resume=r1,
            status="applied",
        )

        # Alice uploads V2 later
        r2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("v2.pdf", b"Version 2 updated resume"),
            version_number=2,
            status="parsed",
            ats_score=85,
        )

        # Confirm application still references V1
        application.refresh_from_db()
        self.assertEqual(application.resume.pk, r1.pk)
        self.assertEqual(application.resume.version_number, 1)

    @patch("apps.candidates.views.extract_text")
    def test_full_upload_workflow_end_to_end(self, mock_extract):
        """Test full view workflow: uploading v1, then uploading v2, checking progress page."""
        mock_extract.return_value = (
            "Alice Smith. Full Stack Engineer. Experience: Python, Django, PostgreSQL. "
            "Education: Master of Computer Applications (MCA)."
        )

        file1 = SimpleUploadedFile("alice_v1.pdf", b"%PDF-1.4 dummy", content_type="application/pdf")
        resp1 = self.client1.post(reverse("candidate_resume"), {"file": file1})
        self.assertEqual(resp1.status_code, 302)

        v1 = self.candidate1.resumes.get(version_number=1)
        self.assertEqual(v1.status, "parsed")
        self.assertIsNotNone(v1.ats_score)
        v1_score = v1.ats_score

        # Second upload with Docker added
        mock_extract.return_value = (
            "Alice Smith. Senior Full Stack Engineer. Experience: Python, Django, PostgreSQL, Docker, AWS. "
            "Education: Master of Computer Applications (MCA). Built scalable microservices."
        )
        file2 = SimpleUploadedFile("alice_v2.pdf", b"%PDF-1.4 dummy 2", content_type="application/pdf")
        resp2 = self.client1.post(reverse("candidate_resume"), {"file": file2})
        self.assertEqual(resp2.status_code, 302)

        v2 = self.candidate1.resumes.get(version_number=2)
        self.assertEqual(v2.status, "parsed")
        self.assertIsNotNone(v2.ats_score)

        # Check Progress Page
        progress_resp = self.client1.get(reverse("candidate_resume_progress"))
        self.assertEqual(progress_resp.status_code, 200)
        self.assertContains(progress_resp, "Resume Progress & Comparison")
        self.assertContains(progress_resp, "Version 1")
        self.assertContains(progress_resp, "Version 2")
        self.assertContains(progress_resp, "ATS Score Progression")
        self.assertContains(progress_resp, "Newly Detected")

        # Check Version 1 Historical Detail Page retains V1 data
        v1_detail_resp = self.client1.get(reverse("candidate_resume_version_detail", kwargs={"pk": v1.pk}))
        self.assertEqual(v1_detail_resp.status_code, 200)
        self.assertContains(v1_detail_resp, f"Resume Version 1 Analysis")
        self.assertContains(v1_detail_resp, f"{v1_score}")


class ResumeVersionDeletionAndMatchingTestCase(TestCase):
    """
    Dedicated test suite for:
    - Feature 1: Delete Resume Versions (older, latest, only remaining, unauthorized, application protection)
    - Feature 2: Verify and Correct AI Job Matching Version Selection (latest analyzed default, fallback, caching, application snapshot)
    """

    def setUp(self):
        cache.clear()
        # Candidate 1 (Alice)
        self.user1 = User.objects.create_user(
            username="alice_tester",
            email="alice_tester@example.com",
            password="password123",
            first_name="Alice",
            last_name="Tester",
        )
        self.candidate1 = Candidate.objects.create(
            user=self.user1,
            headline="Full Stack Python Developer",
            location="San Francisco",
            experience_years=4,
            profile_complete=True,
        )

        # Candidate 2 (Bob - unauthorized user)
        self.user2 = User.objects.create_user(
            username="bob_tester",
            email="bob_tester@example.com",
            password="password123",
            first_name="Bob",
            last_name="Tester",
        )
        self.candidate2 = Candidate.objects.create(
            user=self.user2,
            headline="Frontend React Developer",
            location="Chicago",
            experience_years=2,
            profile_complete=True,
        )

        # Recruiter & Company
        self.recruiter_user = User.objects.create_user(
            username="carol_recruiter",
            email="carol_recruiter@example.com",
            password="password123",
            first_name="Carol",
            last_name="Danvers",
        )
        self.company = Company.objects.create(name="NexGen AI Systems")
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user,
            company=self.company,
            designation="Principal Recruiter",
        )

        # Job Category and Job
        self.category = JobCategory.objects.create(name="Software Engineering")
        self.job = Job.objects.create(
            recruiter=self.recruiter,
            company=self.company,
            title="Senior Python Backend Engineer",
            category=self.category,
            location="Remote",
            description="Looking for an experienced Python developer skilled in Django, PostgreSQL, and Docker.",
            requirements="Python, Django, PostgreSQL, Docker, Microservices",
            status="active",
        )

        # Skills
        self.skill_python = Skill.objects.create(name="Python", category="Backend")
        self.skill_django = Skill.objects.create(name="Django", category="Framework")
        self.skill_docker = Skill.objects.create(name="Docker", category="DevOps")
        self.skill_react = Skill.objects.create(name="React", category="Frontend")
        self.job.skills_required.add(self.skill_python, self.skill_django, self.skill_docker)

        # HTTP Clients
        self.client1 = Client()
        self.client1.force_login(self.user1)

        self.client2 = Client()
        self.client2.force_login(self.user2)

        self.recruiter_client = Client()
        self.recruiter_client.force_login(self.recruiter_user)

    def tearDown(self):
        cache.clear()

    def test_delete_older_version(self):
        """Deleting an older version removes it while keeping the latest and active resume intact."""
        v1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v1.pdf", b"V1 resume content"),
            file_name="alice_v1.pdf",
            version_number=1,
            status="parsed",
            ats_score=60,
            parsed_text="Python Django developer with SQL experience.",
        )
        v2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v2.pdf", b"V2 resume content"),
            file_name="alice_v2.pdf",
            version_number=2,
            status="parsed",
            ats_score=85,
            parsed_text="Senior Python Django developer with Docker and PostgreSQL experience.",
        )

        self.assertEqual(self.candidate1.latest_resume.pk, v2.pk)
        self.assertEqual(self.candidate1.active_resume.pk, v2.pk)

        # GET confirm delete page
        confirm_resp = self.client1.get(reverse("candidate_resume_delete", kwargs={"pk": v1.pk}))
        self.assertEqual(confirm_resp.status_code, 200)
        self.assertContains(confirm_resp, "Delete Resume Version 1")

        # POST delete v1
        del_resp = self.client1.post(reverse("candidate_resume_delete", kwargs={"pk": v1.pk}))
        self.assertEqual(del_resp.status_code, 302)
        self.assertRedirects(del_resp, reverse("candidate_resume_progress"))

        # Verify v1 is removed from DB
        self.assertFalse(Resume.objects.filter(pk=v1.pk).exists())
        self.assertEqual(self.candidate1.resumes.count(), 1)

        # Verify latest and active resume are still v2
        self.assertEqual(self.candidate1.latest_resume.pk, v2.pk)
        self.assertEqual(self.candidate1.active_resume.pk, v2.pk)

    def test_delete_latest_version(self):
        """Deleting the latest version updates the active resume to the newest remaining analyzed version."""
        v1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v1.pdf", b"V1 resume content"),
            file_name="alice_v1.pdf",
            version_number=1,
            status="parsed",
            ats_score=72,
            parsed_text="Python Django backend developer.",
        )
        v2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v2.pdf", b"V2 resume content"),
            file_name="alice_v2.pdf",
            version_number=2,
            status="parsed",
            ats_score=90,
            parsed_text="Senior Python engineer with cloud architecture.",
        )

        self.assertEqual(self.candidate1.latest_resume.pk, v2.pk)
        self.assertEqual(self.candidate1.active_resume.pk, v2.pk)

        # Alice deletes v2
        del_resp = self.client1.post(reverse("candidate_resume_delete", kwargs={"pk": v2.pk}))
        self.assertEqual(del_resp.status_code, 302)

        # Verify v2 is deleted and v1 is now latest and active
        self.assertFalse(Resume.objects.filter(pk=v2.pk).exists())
        self.assertEqual(self.candidate1.resumes.count(), 1)
        self.assertEqual(self.candidate1.latest_resume.pk, v1.pk)
        self.assertEqual(self.candidate1.active_resume.pk, v1.pk)

    def test_delete_only_remaining_version_graceful_zero_state(self):
        """Deleting the only remaining version leaves 0 resumes and does not crash candidate pages."""
        v1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v1.pdf", b"Sole resume content"),
            file_name="alice_v1.pdf",
            version_number=1,
            status="parsed",
            ats_score=68,
            parsed_text="Python software engineer.",
        )

        del_resp = self.client1.post(reverse("candidate_resume_delete", kwargs={"pk": v1.pk}))
        self.assertEqual(del_resp.status_code, 302)
        self.assertEqual(self.candidate1.resumes.count(), 0)
        self.assertIsNone(self.candidate1.latest_resume)
        self.assertIsNone(self.candidate1.active_resume)

        # Verify all candidate pages handle 0 resumes gracefully
        dash_resp = self.client1.get(reverse("candidate_dashboard"))
        self.assertEqual(dash_resp.status_code, 200)

        resume_resp = self.client1.get(reverse("candidate_resume"))
        self.assertEqual(resume_resp.status_code, 200)

        progress_resp = self.client1.get(reverse("candidate_resume_progress"))
        self.assertEqual(progress_resp.status_code, 200)
        self.assertContains(progress_resp, "No resume versions uploaded yet")

        jobs_resp = self.client1.get(reverse("candidate_jobs"))
        self.assertEqual(jobs_resp.status_code, 200)

    def test_prevent_unauthorized_deletion(self):
        """Candidate Bob cannot delete Candidate Alice's resume version."""
        alice_v1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v1.pdf", b"Alice resume"),
            file_name="alice_v1.pdf",
            version_number=1,
            status="parsed",
            ats_score=75,
            parsed_text="Alice credentials",
        )

        # Bob attempts GET confirm delete on Alice's resume -> 404
        get_resp = self.client2.get(reverse("candidate_resume_delete", kwargs={"pk": alice_v1.pk}))
        self.assertEqual(get_resp.status_code, 404)

        # Bob attempts POST delete on Alice's resume -> 404
        post_resp = self.client2.post(reverse("candidate_resume_delete", kwargs={"pk": alice_v1.pk}))
        self.assertEqual(post_resp.status_code, 404)

        # Alice's resume is preserved
        self.assertTrue(Resume.objects.filter(pk=alice_v1.pk).exists())

    def test_preserving_resumes_linked_to_job_applications(self):
        """Resumes submitted with job applications cannot be deleted, preserving recruiter document access."""
        v1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_app_v1.pdf", b"%PDF-1.4 Application Resume"),
            file_name="alice_app_v1.pdf",
            version_number=1,
            status="parsed",
            ats_score=70,
            parsed_text="Alice Python Developer",
        )

        # Alice applies for the job with v1
        app = Application.objects.create(
            job=self.job,
            candidate=self.candidate1,
            resume=v1,
            match_score=75,
            status="applied",
        )

        # Alice uploads v2 later
        v2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v2.pdf", b"%PDF-1.4 New Resume"),
            file_name="alice_v2.pdf",
            version_number=2,
            status="parsed",
            ats_score=90,
            parsed_text="Alice Senior Python Developer with Docker",
        )

        # Alice attempts to delete v1 (which is linked to application)
        del_resp = self.client1.post(reverse("candidate_resume_delete", kwargs={"pk": v1.pk}))
        self.assertEqual(del_resp.status_code, 302)

        # v1 must still exist in DB
        self.assertTrue(Resume.objects.filter(pk=v1.pk).exists())
        self.assertEqual(app.resume.pk, v1.pk)

        # Verify recruiter Carol can still view and download Alice's submitted resume
        view_resp = self.recruiter_client.get(reverse("jobs:application_resume_view", kwargs={"pk": app.pk}))
        self.assertEqual(view_resp.status_code, 200)

        download_resp = self.recruiter_client.get(reverse("jobs:application_resume_download", kwargs={"pk": app.pk}))
        self.assertEqual(download_resp.status_code, 200)

    def test_job_matching_uses_latest_successfully_analyzed_resume_version(self):
        """New job recommendations and match calculations default to the latest successfully analyzed version."""
        v1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v1.pdf", b"content"),
            version_number=1,
            status="parsed",
            ats_score=40,
            parsed_text="Junior developer with basic skills.",
            analysis_data={"extracted_skills": ["HTML"]},
        )
        self.assertEqual(self.candidate1.active_resume.pk, v1.pk)
        score_v1 = calculate_hybrid_match_score(self.candidate1, self.job)

        # Upload v2 with high skill overlap and successful analysis
        v2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v2.pdf", b"content 2"),
            version_number=2,
            status="parsed",
            ats_score=95,
            parsed_text="Senior Python and Django developer with Docker, PostgreSQL, and microservices experience.",
            analysis_data={"extracted_skills": ["Python", "Django", "Docker"]},
        )
        self.assertEqual(self.candidate1.active_resume.pk, v2.pk)

        score_v2 = calculate_hybrid_match_score(self.candidate1, self.job)
        self.assertGreater(score_v2, score_v1)

    def test_failed_or_pending_analysis_fallback_handling(self):
        """Failed or pending upload does not replace the last successfully analyzed version in matching."""
        v1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v1.pdf", b"content 1"),
            version_number=1,
            status="parsed",
            ats_score=78,
            parsed_text="Python Django backend engineer.",
        )
        self.assertEqual(self.candidate1.active_resume.pk, v1.pk)

        # Alice uploads v2 but it fails during analysis
        v2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v2_corrupted.pdf", b"corrupted"),
            version_number=2,
            status="error",
            ats_score=None,
            parsed_text="",
        )

        # Latest resume is v2, but active resume must remain v1!
        self.assertEqual(self.candidate1.latest_resume.pk, v2.pk)
        self.assertEqual(self.candidate1.active_resume.pk, v1.pk)

        matching_status = get_candidate_matching_status(self.candidate1)
        self.assertTrue(matching_status["is_fallback"])
        self.assertEqual(matching_status["active_version"], 1)
        self.assertEqual(matching_status["latest_version"], 2)

        # Job matching calculation still works safely using v1
        score = calculate_hybrid_match_score(self.candidate1, self.job)
        self.assertGreater(score, 0)

        # Candidate dashboard displays fallback notice banner
        dash_resp = self.client1.get(reverse("candidate_dashboard"))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, "Active Matching Source: Resume Version 1")

        # Candidate jobs page displays fallback notice banner
        jobs_resp = self.client1.get(reverse("candidate_jobs"))
        self.assertEqual(jobs_resp.status_code, 200)
        self.assertContains(jobs_resp, "Match Scores Powered by Resume Version 1")

    def test_old_application_records_retains_submitted_resume_and_match_score(self):
        """Submitting an application snapshots the current resume and match score, persisting over future versions."""
        v1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v1.pdf", b"V1 content"),
            version_number=1,
            status="parsed",
            ats_score=70,
            parsed_text="Python Django developer",
        )

        # Alice applies for the job via POST
        apply_resp = self.client1.post(reverse("candidate_job_detail", kwargs={"pk": self.job.pk}))
        self.assertEqual(apply_resp.status_code, 302)

        app = Application.objects.get(candidate=self.candidate1, job=self.job)
        self.assertEqual(app.resume.pk, v1.pk)
        self.assertIsNotNone(app.match_score)
        v1_app_score = app.match_score

        # Alice later uploads v2 with higher score
        v2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v2.pdf", b"V2 content"),
            version_number=2,
            status="parsed",
            ats_score=95,
            parsed_text="Python Django Docker PostgreSQL Kubernetes Lead",
        )

        # Verify application still references v1 and retains original match_score
        app.refresh_from_db()
        self.assertEqual(app.resume.pk, v1.pk)
        self.assertEqual(app.resume.version_number, 1)
        self.assertEqual(app.match_score, v1_app_score)

    def test_cached_match_scores_invalidation_and_staleness(self):
        """Cached match scores detect version change, mark stale, and refresh on cache invalidation."""
        v1 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v1.pdf", b"V1"),
            version_number=1,
            status="parsed",
            ats_score=60,
            parsed_text="Basic developer",
        )

        # Compute and cache match
        matches_v1 = calculate_job_matches(self.candidate1, [self.job])
        self.assertEqual(len(matches_v1), 1)

        # Read cache via get_cached_job_match
        score_v1, is_stale_v1, ver_v1 = get_cached_job_match(self.candidate1, self.job)
        self.assertFalse(is_stale_v1)
        self.assertEqual(ver_v1, 1)

        # Add v2 without immediately invalidating cache
        v2 = Resume.objects.create(
            candidate=self.candidate1,
            file=SimpleUploadedFile("alice_v2.pdf", b"V2"),
            version_number=2,
            status="parsed",
            ats_score=90,
            parsed_text="Python Django Docker Expert",
        )

        # get_cached_job_match detects that cached version (1) != active version (2)
        score_stale, is_stale_now, ver_stale = get_cached_job_match(self.candidate1, self.job)
        self.assertTrue(is_stale_now)
        self.assertEqual(ver_stale, 1)

        # Invalidate cache
        cache_key = f"cm_job_match:{self.candidate1.id}:{self.job.id}"
        invalidate_candidate_match_cache(self.candidate1)
        self.assertIsNone(cache.get(cache_key))

        # Recalculate with v2
        matches_v2 = calculate_job_matches(self.candidate1, [self.job])
        score_v2, is_stale_v2, ver_v2 = get_cached_job_match(self.candidate1, self.job)
        self.assertFalse(is_stale_v2)
        self.assertEqual(ver_v2, 2)
