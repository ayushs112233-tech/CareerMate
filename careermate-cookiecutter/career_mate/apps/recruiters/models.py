from django.conf import settings
from django.db import models


class Company(models.Model):
    """
    Organization or employer posting jobs on CareerMate AI.
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    industry = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Information Technology, Healthcare, Finance",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


class Recruiter(models.Model):
    """
    Profile representing a hiring manager or company recruiter.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recruiter_profile",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recruiters",
    )
    designation = models.CharField(
        max_length=150,
        blank=True,
        help_text="e.g. Technical Recruiter, HR Director",
    )
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Recruiter"
        verbose_name_plural = "Recruiters"

    def __str__(self):
        comp_name = self.company.name if self.company else "Independent"
        return f"{self.user.username} ({comp_name})"
