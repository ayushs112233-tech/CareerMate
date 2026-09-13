from django import forms

from apps.candidates.models import Candidate
from apps.resume.models import Resume


class CandidateProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = Candidate
        fields = ["first_name", "last_name", "email", "headline", "phone", "location", "bio", "experience_years", "education", "skills"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 5}), "education": forms.Textarea(attrs={"rows": 4}), "skills": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.instance.user.first_name
        self.fields["last_name"].initial = self.instance.user.last_name
        self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        candidate = super().save(commit=False)
        user = candidate.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        candidate.profile_complete = all([user.first_name or user.last_name, user.email, candidate.headline, candidate.phone, candidate.location, candidate.bio, candidate.education, candidate.skills.exists() or bool(self.cleaned_data.get("skills"))])
        if commit:
            user.save(update_fields=["first_name", "last_name", "email"])
            candidate.save()
            self.save_m2m()
        return candidate


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ["file"]
        widgets = {"file": forms.ClearableFileInput(attrs={"accept": ".pdf,.doc,.docx"})}

    def save(self, candidate, commit=True):
        resume = super().save(commit=False)
        resume.candidate = candidate
        resume.file_name = resume.file.name
        resume.status = "uploaded"
        if commit:
            resume.save()
        return resume