from django.db import models


class Resume(models.Model):
    """
    Resume file uploaded by a candidate for screening and job applications.
    """
    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("parsed", "Parsed"),
        ("error", "Processing Error"),
    ]

    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="resumes",
    )
    version_number = models.PositiveIntegerField(
        default=1,
        help_text="Sequential version number for this candidate's resume history",
    )
    file = models.FileField(upload_to="resumes/%Y/%m/")
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    parsed_text = models.TextField(
        blank=True,
        help_text="Extracted text from resume for keyword and skill matching",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="uploaded",
    )
    ats_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Historical ATS score snapshot calculated at upload time",
    )
    analysis_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Historical snapshot of ATS breakdown, extracted skills, suggestions, and metrics",
    )
    scoring_version = models.CharField(
        max_length=20,
        default="v1.0",
        help_text="Ruleset/algorithm version used for ATS scoring",
    )

    class Meta:
        ordering = ["-version_number", "-uploaded_at"]
        unique_together = ("candidate", "version_number")
        verbose_name = "Resume"
        verbose_name_plural = "Resumes"

    def __str__(self):
        return f"{self.candidate} - v{self.version_number} ({self.file_name})"

    def save(self, *args, **kwargs):
        if self._state.adding and self.candidate_id:
            existing_versions = set(
                Resume.objects.filter(candidate_id=self.candidate_id).values_list("version_number", flat=True)
            )
            if not self.version_number or self.version_number in existing_versions:
                max_ver = Resume.objects.filter(candidate_id=self.candidate_id).aggregate(
                    models.Max("version_number")
                )["version_number__max"]
                self.version_number = (max_ver + 1) if max_ver else 1
        super().save(*args, **kwargs)

    @property
    def file_exists(self):
        """Check if the physical file exists in storage."""
        try:
            return bool(self.file and self.file.name and self.file.storage.exists(self.file.name))
        except Exception:
            return False

    @property
    def is_latest(self):
        """Check if this resume is the candidate's latest uploaded version."""
        latest = self.candidate.resumes.order_by("-version_number").first()
        return latest and latest.id == self.id

    @property
    def is_latest_analyzed(self):
        """Check if this resume is the candidate's latest successfully analyzed version."""
        latest_analyzed = (
            self.candidate.resumes.filter(status="parsed", ats_score__isnull=False)
            .order_by("-version_number")
            .first()
        )
        return latest_analyzed and latest_analyzed.id == self.id

    @property
    def extracted_skills_list(self):
        """Return list of skill names extracted in this historical version."""
        if isinstance(self.analysis_data, dict):
            return self.analysis_data.get("extracted_skills", [])
        return []

    @property
    def suggestions_list(self):
        """Return list of suggestions associated with this historical version."""
        if isinstance(self.analysis_data, dict):
            return self.analysis_data.get("suggestions", [])
        return []

    @property
    def breakdown_list(self):
        """Return ATS breakdown metrics associated with this historical version."""
        if isinstance(self.analysis_data, dict):
            return self.analysis_data.get("breakdown", [])
        return []
