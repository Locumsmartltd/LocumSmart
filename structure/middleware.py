from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

class RoleBasedAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Define restricted paths and allowed roles
        restricted_paths = {
            '/appAdmin/': 'admin',
            '/locum/': 'locum',
        }

        # Define publicly accessible paths
        public_paths = [
            '/locum/employerRequest/',
            '/locum/locumTypes/',
            '/locum/pharmacistRegister/',
            '/locum/gpRegistration/',
            '/locum/techRegistration/',
            '/locum/nurseRegistration/',
        ]

        # Allow public paths without checks
        if request.path in public_paths:
            return self.get_response(request)
        
        # Special case for locum edit path
        if request.path.startswith('/appAdmin/locums/') and request.path.endswith('/edit/'):
            if not request.user.is_authenticated:
                return redirect('login')  # Redirect to login if not logged in
            else:  # Allow both roles
                return self.get_response(request)

        for path, role in restricted_paths.items():
            if request.path.startswith(path):
                if not request.user.is_authenticated:
                    return redirect('login')  # Redirect to login if not logged in
                if role == 'admin' and not hasattr(request.user, 'admin'):  # Check for admin role
                    raise PermissionDenied
                if role == 'locum' and not hasattr(request.user, 'locum'):  # Example custom role
                    raise PermissionDenied

        return self.get_response(request)
