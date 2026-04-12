"""
cockpit/authentication.py

Session-based authentication for the Config Cockpit REST API.

The Cockpit uses Django's own session framework (cookie-based) so users log
in with their Django username + password — completely independent of DSpace JWT.

Usage
-----
Add to REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] *before*
DSpaceJWTAuthentication so the cockpit endpoints are matched first:

    "cockpit.authentication.CockpitSessionAuthentication",

The cockpit login view sets request.session["cockpit_user_id"] = user.pk.
This authenticator reads that key and returns the Django User object.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication

User = get_user_model()


class CockpitSessionAuthentication(BaseAuthentication):
    """
    Authenticates requests that carry a Django session containing
    ``cockpit_user_id``.  Returns (user, None) on success, None otherwise
    (falling through to the next authenticator in the list).
    """

    def authenticate(self, request):
        user_id = request.session.get("cockpit_user_id")
        if not user_id:
            return None
        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None
        return (user, None)

    def authenticate_header(self, request):
        # Returning None keeps DRF from overriding the 401 with a WWW-Authenticate header.
        return None
