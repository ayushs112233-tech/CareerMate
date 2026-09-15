from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

def is_candidate(user):
    return user.is_authenticated and hasattr(user, 'candidate_profile')

def is_recruiter(user):
    return user.is_authenticated and hasattr(user, 'recruiter_profile')

def candidate_required(function=None, login_url='accounts:login'):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(login_url)
            if not hasattr(request.user, 'candidate_profile'):
                raise PermissionDenied("You must be a candidate to access this page.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    if function:
        return decorator(function)
    return decorator
