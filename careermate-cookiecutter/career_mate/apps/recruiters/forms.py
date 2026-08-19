from django import forms
from .models import CandidateApplication, CompanyProfile, JobPosting


class CompanyProfileForm(forms.ModelForm):
	class Meta:
		model = CompanyProfile
		fields = ["name", "industry", "location", "website", "description"]
		widgets = {"description": forms.Textarea(attrs={"rows": 5})}


class JobPostingForm(forms.ModelForm):
	class Meta:
		model = JobPosting
		fields = ["title", "department", "location", "work_mode", "description", "required_skills", "is_active"]
		widgets = {"description": forms.Textarea(attrs={"rows": 7})}


class CandidateStatusForm(forms.ModelForm):
	class Meta:
		model = CandidateApplication
		fields = ["status"]
