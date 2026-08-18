from django import forms
from apps.candidates.models import Skill
from apps.jobs.models import Application, Job, JobCategory
from apps.recruiters.models import Company


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ["name", "category"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Python, Docker"}),
            "category": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Programming, Database"}),
        }


class JobCategoryForm(forms.ModelForm):
    class Meta:
        model = JobCategory
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Software Engineering"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Category description..."}),
        }


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "industry", "website", "location", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Company name"}),
            "industry": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Information Technology"}),
            "website": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://example.com"}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "City, Country"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Company description..."}),
        }


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "title",
            "company",
            "recruiter",
            "category",
            "employment_type",
            "location",
            "min_experience",
            "salary_min",
            "salary_max",
            "status",
            "skills_required",
            "description",
            "requirements",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Senior Python Developer"}),
            "company": forms.Select(attrs={"class": "form-select"}),
            "recruiter": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "employment_type": forms.Select(attrs={"class": "form-select"}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Bangalore / Remote"}),
            "min_experience": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "salary_min": forms.NumberInput(attrs={"class": "form-control", "step": "1000", "placeholder": "Min salary"}),
            "salary_max": forms.NumberInput(attrs={"class": "form-control", "step": "1000", "placeholder": "Max salary"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "skills_required": forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Role responsibilities..."}),
            "requirements": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Qualifications and requirements..."}),
        }


class ApplicationStatusForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
        }
