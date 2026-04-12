from django.urls import path
from . import views

# All mounted under /api/cockpit/auth/  (see dspace_config/urls.py)
urlpatterns = [
    path("csrf/",   views.CsrfView.as_view(),   name="cockpit-csrf"),
    path("login/",  views.LoginView.as_view(),   name="cockpit-login"),
    path("logout/", views.LogoutView.as_view(),  name="cockpit-logout"),
    path("me/",     views.MeView.as_view(),      name="cockpit-me"),
]
