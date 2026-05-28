from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class OnboardingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Bypass specific paths
            bypassed_paths = [
                reverse('onboarding'),
                reverse('logout'),
                '/admin/',
                '/securelogin/',
            ]
            
            # Allow media/static
            if request.path.startswith(settings.MEDIA_URL) or request.path.startswith(settings.STATIC_URL):
                return self.get_response(request)

            is_bypassed = any(request.path.startswith(path) for path in bypassed_paths)

            if not is_bypassed:
                # Check for skip flag
                if not request.session.get('skip_onboarding', False):
                    # Check if user lacks phone number or primary address
                    needs_onboarding = False
                    
                    if not request.user.phone_number:
                        needs_onboarding = True
                        
                    if hasattr(request.user, 'userprofile'):
                        if not request.user.userprofile.address_line_1:
                            needs_onboarding = True
                            
                    if needs_onboarding:
                        return redirect('onboarding')

        response = self.get_response(request)
        return response
