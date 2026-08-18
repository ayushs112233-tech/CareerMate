from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import RegistrationForm


def register(request):
    """Register a user through Django's built-in password-hashing form."""
    if request.user.is_authenticated:
        return redirect("accounts:login")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("accounts:login")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


class UserLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("accounts:login")


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")
