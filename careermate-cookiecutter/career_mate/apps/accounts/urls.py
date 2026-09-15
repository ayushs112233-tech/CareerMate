from django.urls import path

from .views import (
    CandidateRegistrationView,
    RecruiterRegistrationView,
    RegisterChoiceView,
    UserLoginView,
    UserLogoutView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterChoiceView.as_view(), name="register"),
    path("register/candidate/", CandidateRegistrationView.as_view(), name="register_candidate"),
    path("register/recruiter/", RecruiterRegistrationView.as_view(), name="register_recruiter"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
]
