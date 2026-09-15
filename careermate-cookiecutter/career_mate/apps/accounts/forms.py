from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from apps.candidates.models import Candidate
from apps.recruiters.models import Recruiter, Company


class BaseRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email


class CandidateRegistrationForm(BaseRegistrationForm):
    """Register a User and their Candidate profile atomically."""

    headline = forms.CharField(max_length=255, required=False, help_text="e.g. Full Stack Developer")
    
    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            Candidate.objects.create(
                user=user,
                headline=self.cleaned_data.get('headline', '')
            )
        return user


class RecruiterRegistrationForm(BaseRegistrationForm):
    """Register a User and their Recruiter profile atomically, along with an initial Company if provided."""

    company_name = forms.CharField(max_length=255, required=False, help_text="Your company's name")
    designation = forms.CharField(max_length=150, required=False, help_text="e.g. Technical Recruiter")

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            
            # Create Company if provided
            company = None
            company_name = self.cleaned_data.get('company_name')
            if company_name:
                company, _ = Company.objects.get_or_create(name=company_name)
                
            Recruiter.objects.create(
                user=user,
                company=company,
                designation=self.cleaned_data.get('designation', '')
            )
        return user
