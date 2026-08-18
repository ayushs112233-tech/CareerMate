from django.db import models


class JobCategory(models.Model):
    """
    Industry domain or functional classification for jobs.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Job Category"
        verbose_name_plural = "Job Categories"

    def __str__(self):
        return self.name


class Job(models.Model):
    """
    Job vacancy posting published by a recruiter/company.
    """
    EMPLOYMENT_TYPES = [
        ("full_time", "Full Time"),
        ("part_time", "Part Time"),
        ("contract", "Contract"),
        ("internship", "Internship"),
        ("remote", "Remote"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed"),
    ]

    title = models.CharField(max_length=255)
    recruiter = models.ForeignKey(
        "recruiters.Recruiter",
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    company = models.ForeignKey(
        "recruiters.Company",
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    category = models.ForeignKey(
        JobCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )
    description = models.TextField(help_text="Detailed job description and responsibilities")
    requirements = models.TextField(blank=True, help_text="Minimum qualifications, prerequisites")
    location = models.CharField(max_length=255, help_text="e.g. Bangalore, India or Remote")
    employment_type = models.CharField(
        max_length=50,
        choices=EMPLOYMENT_TYPES,
        default="full_time",
    )
    min_experience = models.PositiveIntegerField(
        default=0,
        help_text="Minimum required experience in years",
    )
    salary_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum salary offer",
    )
    salary_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum salary offer",
    )
    skills_required = models.ManyToManyField(
        "candidates.Skill",
        blank=True,
        related_name="jobs",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Job"
        verbose_name_plural = "Jobs"

    def __str__(self):
        return f"{self.title} @ {self.company.name}"


class Application(models.Model):
    """
    Job application submitted by a candidate for a specific job posting.
    """
    STATUS_CHOICES = [
        ("applied", "Applied"),
        ("under_review", "Under Review"),
        ("shortlisted", "Shortlisted"),
        ("interview", "Interview"),
        ("rejected", "Rejected"),
        ("hired", "Hired"),
    ]

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="applications",
    )
    resume = models.ForeignKey(
        "resume.Resume",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="applied",
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_at"]
        unique_together = ("job", "candidate")
        verbose_name = "Application"
        verbose_name_plural = "Applications"

    def __str__(self):
        return f"Application: {self.candidate} -> {self.job.title}"
