from django import forms

from apps.candidates.models import Skill
from .models import Job, JobCategory


class JobForm(forms.ModelForm):
	category_name = forms.CharField(required=False, label="Category", widget=forms.TextInput(attrs={"placeholder": "e.g. Software Engineering"}))
	required_skills = forms.CharField(required=False, label="Required skills", help_text="Separate skills with commas.", widget=forms.TextInput(attrs={"placeholder": "Python, Django, PostgreSQL"}))

	class Meta:
		model = Job
		fields = ("title", "category_name", "description", "requirements", "required_skills", "location", "employment_type", "min_experience", "salary_min", "salary_max", "status")
		widgets = {"description": forms.Textarea(attrs={"rows": 7}), "requirements": forms.Textarea(attrs={"rows": 5})}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if self.instance.pk:
			self.fields["category_name"].initial = self.instance.category.name if self.instance.category else ""
			self.fields["required_skills"].initial = ", ".join(self.instance.skills_required.values_list("name", flat=True))

	def save(self, commit=True):
		job = super().save(commit=False)
		category_name = self.cleaned_data["category_name"].strip()
		skill_names = {item.strip() for item in self.cleaned_data["required_skills"].split(",") if item.strip()}
		job.category = JobCategory.objects.get_or_create(name=category_name)[0] if category_name else None
		if commit:
			job.save()
			job.skills_required.set([Skill.objects.get_or_create(name=name)[0] for name in sorted(skill_names)])
			self.save_m2m()
		return job
