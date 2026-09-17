from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from django.contrib.auth import login

from .forms import CandidateRegistrationForm, RecruiterRegistrationForm
from .decorators import is_candidate, is_recruiter


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        
        # Determine redirection based on role
        if hasattr(user, 'candidate_profile'):
            return reverse_lazy("candidate_dashboard")
        elif hasattr(user, 'recruiter_profile'):
            return reverse_lazy("recruiters:dashboard")
        elif user.is_staff or user.is_superuser:
            return reverse_lazy("admin_panel:dashboard")
            
        # Fallback if no specific role profile is found
        return reverse_lazy("home")


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


class RegisterChoiceView(TemplateView):
    template_name = "accounts/register_choice.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)


class CandidateRegistrationView(CreateView):
    form_class = CandidateRegistrationForm
    template_name = "accounts/register_candidate.html"
    success_url = reverse_lazy("candidate_dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Save user and candidate profile, then log in
        user = form.save()
        login(self.request, user)
        return redirect(self.success_url)


class RecruiterRegistrationView(CreateView):
    form_class = RecruiterRegistrationForm
    template_name = "accounts/register_recruiter.html"
    success_url = reverse_lazy("recruiters:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Save user and recruiter profile, then log in
        user = form.save()
        login(self.request, user)
        return redirect(self.success_url)
