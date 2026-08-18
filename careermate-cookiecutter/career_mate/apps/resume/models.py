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

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Resume"
        verbose_name_plural = "Resumes"

    def __str__(self):
        return f"{self.candidate} - {self.file_name}"
