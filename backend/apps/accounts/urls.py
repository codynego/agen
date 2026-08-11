from django.urls import path

from .views import CsrfTokenView, LogoutView, MeView, RequestLoginCodeView, VerifyLoginCodeView

urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("request-code/", RequestLoginCodeView.as_view(), name="auth-request-code"),
    path("verify-code/", VerifyLoginCodeView.as_view(), name="auth-verify-code"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
]
