from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from appAdmin.models import Admin  # Import your Admin model

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            obj=Admin.objects.get(id=request.user.id)
            print('logged in')
            print(isinstance(request.user, Admin))
            print(request.user)
            # Check if the authenticated user is an instance of the Admin model
            if obj :
                print('not instance')
                return view_func(request, *args, **kwargs)
            else:
                
                return redirect('LandingPage')  # Redirect to the homepage or any other view
        else:
            # Handle unauthenticated users (optional)
            messages.error(request, 'Please log in to continue.')
            return redirect('LandingPage')  # Redirect to the login page

    return _wrapped_view