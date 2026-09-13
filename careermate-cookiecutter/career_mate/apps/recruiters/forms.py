from django import forms

from .models import Company, Recruiter


class RecruiterProfileForm(forms.ModelForm):
	first_name = forms.CharField(max_length=150, required=False)
	last_name = forms.CharField(max_length=150, required=False)
	email = forms.EmailField(required=False)

	class Meta:
		model = Recruiter
		fields = ("first_name", "last_name", "email", "designation", "phone")

	def __init__(self, *args, **kwargs):
		self.user = kwargs.pop("user", None)
		super().__init__(*args, **kwargs)
		if self.user:
			for name in ("first_name", "last_name", "email"):
				self.fields[name].initial = getattr(self.user, name)

	def save(self, commit=True):
		recruiter = super().save(commit=False)
		user = self.user or recruiter.user
		user.first_name = self.cleaned_data["first_name"]
		user.last_name = self.cleaned_data["last_name"]
		user.email = self.cleaned_data["email"]
		if commit:
			user.save(update_fields=["first_name", "last_name", "email"])
			recruiter.save()
		return recruiter


class CompanyForm(forms.ModelForm):
	class Meta:
		model = Company
		fields = ("name", "description", "website", "location", "industry")
		widgets = {"description": forms.Textarea(attrs={"rows": 5})}
