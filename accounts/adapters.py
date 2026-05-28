from django.utils.text import slugify

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import Account


class NexusKartSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        email = (data.get("email") or user.email or "").strip().lower()
        first_name = data.get("first_name") or data.get("given_name") or ""
        last_name = data.get("last_name") or data.get("family_name") or ""

        user.email = email
        user.first_name = first_name[:50]
        user.last_name = last_name[:50]
        user.username = self._unique_username(email, first_name)
        user.is_active = True
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        if not user.username:
            user.username = self._unique_username(user.email, user.first_name)
            user.save(update_fields=["username"])
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        return user

    def _unique_username(self, email, first_name=""):
        base = slugify((email or "").split("@")[0] or first_name or "user")
        base = (base or "user")[:45]
        username = base
        counter = 1

        while Account.objects.filter(username=username).exists():
            suffix = str(counter)
            username = f"{base[:50 - len(suffix)]}{suffix}"
            counter += 1

        return username
