from django.conf import settings
from django.db import models


class Skill(models.Model):
    """
    Standardized skill entity that can be associated with candidates and job requirements.
    """
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Programming, Framework, Database, Soft Skill",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Skill"
        verbose_name_plural = "Skills"

    def __str__(self):
        return self.name


class Candidate(models.Model):
    """
    Profile representing a job-seeking candidate.
    Links to Django's authentication User model.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="candidate_profile",
    )
    headline = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g. Full Stack Developer | Python & React",
    )
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True, help_text="Short bio or professional summary")
    experience_years = models.PositiveIntegerField(
        default=0,
        help_text="Total years of professional experience",
    )
    education = models.TextField(
        blank=True,
        help_text="Educational background, degree, or university details",
    )
    skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="candidates",
    )
    profile_complete = models.BooleanField(
        default=False,
        help_text="Designates whether the candidate profile is fully filled out",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Candidate"
        verbose_name_plural = "Candidates"

    def __str__(self):
        user_display = getattr(self.user, "get_full_name", None)
        full_name = user_display() if callable(user_display) else ""
        if full_name:
            return f"{full_name} ({self.user.username})"
        return self.user.username
