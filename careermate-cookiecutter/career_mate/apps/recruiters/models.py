from django.conf import settings
from django.db import models
from django.urls import reverse


class CompanyProfile(models.Model):
	owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_profile")
	name = models.CharField(max_length=120)
	industry = models.CharField(max_length=80, blank=True)
	location = models.CharField(max_length=120, blank=True)
	website = models.URLField(blank=True)
	description = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.name


class JobPosting(models.Model):
	class WorkMode(models.TextChoices):
		ONSITE = "On-site", "On-site"
		HYBRID = "Hybrid", "Hybrid"
		REMOTE = "Remote", "Remote"

	company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name="jobs")
	title = models.CharField(max_length=120)
	department = models.CharField(max_length=100, blank=True)
	location = models.CharField(max_length=120, blank=True)
	work_mode = models.CharField(max_length=20, choices=WorkMode.choices, default=WorkMode.HYBRID)
	description = models.TextField()
	required_skills = models.CharField(max_length=300, help_text="Separate skills with commas")
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return self.title

	def get_absolute_url(self):
		return reverse("recruiters:job_detail", args=[self.pk])


class CandidateApplication(models.Model):
	class Status(models.TextChoices):
		NEW = "new", "New"
		REVIEWING = "reviewing", "Reviewing"
		SHORTLISTED = "shortlisted", "Shortlisted"
		REJECTED = "rejected", "Rejected"

	job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="applications")
	candidate_name = models.CharField(max_length=120)
	candidate_email = models.EmailField()
	resume = models.FileField(upload_to="resumes/", blank=True)
	cover_note = models.TextField(blank=True)
	compatibility_score = models.PositiveSmallIntegerField(default=0)
	matched_skills = models.CharField(max_length=300, blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
	applied_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-compatibility_score", "-applied_at"]

	def __str__(self):
		return f"{self.candidate_name} - {self.job.title}"
