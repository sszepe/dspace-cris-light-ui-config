from __future__ import annotations
import requests
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

class DSpaceUser:
    is_authenticated = True
    is_anonymous = False
    def __init__(self, email, name, groups):
        self.email = self.username = email
        self.name = name
        self.groups = groups
    @property
    def is_admin(self):
        return "Administrator" in self.groups
    def __str__(self): return self.email

class DSpaceJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[len("Bearer "):]
        base = settings.DSPACE_BASE_URL.rstrip("/")
        try:
            r = requests.get(f"{base}/api/authn/status",
                             headers={"Authorization": f"Bearer {token}"}, timeout=5)
        except requests.RequestException as e:
            raise AuthenticationFailed(f"DSpace unreachable: {e}")
        if r.status_code != 200:
            raise AuthenticationFailed("DSpace token validation failed")
        data = r.json()
        if not data.get("authenticated"):
            raise AuthenticationFailed("Token not authenticated")
        email  = data.get("_links", {}).get("eperson", {}).get("href", "")
        name   = data.get("name", email)
        groups = [g.get("name","") for g in data.get("_embedded",{}).get("specialGroups",[])]
        return (DSpaceUser(email or name, name, groups), token)
    def authenticate_header(self, request): return "Bearer"
