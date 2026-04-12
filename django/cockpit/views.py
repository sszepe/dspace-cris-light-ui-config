"""
cockpit/views.py

Four thin endpoints used exclusively by the Config Cockpit frontend:

  POST /api/cockpit/auth/login/   { username, password } → { id, username, email, is_staff, is_superuser }
  POST /api/cockpit/auth/logout/  → {}
  GET  /api/cockpit/auth/me/      → { id, username, email, is_staff, is_superuser }
  GET  /api/cockpit/auth/csrf/    → { csrfToken }  (used on first load to seed the cookie)

All four are exempt from the DSpaceJWTAuthentication guard — the cockpit
uses Django sessions only.
"""
from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import CockpitSessionAuthentication

User = get_user_model()


def _user_payload(user):
    return {
        "id": user.pk,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


class CsrfView(APIView):
    """GET /api/cockpit/auth/csrf/ — seeds the CSRF cookie for the SPA."""
    authentication_classes = [CockpitSessionAuthentication]
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    """
    POST /api/cockpit/auth/login/
    Body: { "username": "...", "password": "..." }

    We exempt CSRF here because the SPA calls this before it has a CSRF
    cookie.  After a successful login it fetches /csrf/ which sets the cookie.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")

        if not username or not password:
            return Response({"detail": "Username and password are required."}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=401)
        if not user.is_active:
            return Response({"detail": "Account is disabled."}, status=403)

        # Store in session (creates the session / rotates the session key)
        request.session.cycle_key()
        request.session["cockpit_user_id"] = user.pk
        request.session.save()

        return Response(_user_payload(user))


class LogoutView(APIView):
    """POST /api/cockpit/auth/logout/"""
    authentication_classes = [CockpitSessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        request.session.flush()
        return Response({"detail": "Logged out."})


class MeView(APIView):
    """GET /api/cockpit/auth/me/ — returns current user or 401."""
    authentication_classes = [CockpitSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_payload(request.user))
