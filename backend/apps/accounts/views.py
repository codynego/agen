import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agents.serializers import AgentSerializer
from apps.agents.services import provision_personal_agent
from apps.profiles.models import UserProfile

from .models import EmailLoginChallenge
from .serializers import RequestLoginCodeSerializer, UserSerializer, VerifyLoginCodeSerializer


User = get_user_model()
GENERIC_CODE_MESSAGE = "If this email can receive messages, a sign-in code has been sent."


def auth_payload(user, request):
    agent, _ = provision_personal_agent(user)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return {
        "user": UserSerializer(user).data,
        "personal_agent": AgentSerializer(agent, context={"request": request}).data,
        "onboarding_completed": profile.onboarding_completed,
        "approval_mode": profile.approval_mode,
    }


def request_ip(request):
    return request.META.get("REMOTE_ADDR") or None


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RequestLoginCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestLoginCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        ip_address = request_ip(request)
        now = timezone.now()
        rate_window = now - timedelta(minutes=settings.AUTH_CODE_RATE_WINDOW_MINUTES)

        recent_email_requests = EmailLoginChallenge.objects.filter(email=email, created_at__gte=rate_window).count()
        recent_ip_requests = EmailLoginChallenge.objects.filter(requested_ip=ip_address, created_at__gte=rate_window).count() if ip_address else 0
        if recent_email_requests >= settings.AUTH_CODE_EMAIL_LIMIT or recent_ip_requests >= settings.AUTH_CODE_IP_LIMIT:
            return Response(
                {"detail": "Too many code requests. Please wait before trying again."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        EmailLoginChallenge.objects.filter(email=email, consumed_at__isnull=True).update(consumed_at=now)
        development_code = settings.AUTH_DEV_LOGIN_CODE if settings.DEBUG else ""
        code = development_code or f"{secrets.randbelow(1_000_000):06d}"
        challenge = EmailLoginChallenge.objects.create(
            email=email,
            display_name=serializer.validated_data.get("name", "").strip(),
            code_hash=make_password(code),
            requested_ip=ip_address,
            expires_at=now + timedelta(minutes=settings.AUTH_CODE_TTL_MINUTES),
        )

        try:
            send_mail(
                subject="Your Agen sign-in code",
                message=f"Your Agen sign-in code is {code}. It expires in {settings.AUTH_CODE_TTL_MINUTES} minutes.\n\nIf you did not request this code, you can ignore this email.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception:
            challenge.delete()
            return Response(
                {"detail": "We could not send the code. Please try again shortly."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            "detail": GENERIC_CODE_MESSAGE,
            "challenge_id": challenge.challenge_id,
            "expires_in_seconds": settings.AUTH_CODE_TTL_MINUTES * 60,
        })


@method_decorator(csrf_protect, name="dispatch")
class VerifyLoginCodeView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = VerifyLoginCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        now = timezone.now()

        challenge = EmailLoginChallenge.objects.select_for_update().filter(
            challenge_id=serializer.validated_data["challenge_id"],
        ).first()
        if challenge is None or challenge.consumed_at or challenge.expires_at <= now:
            return Response({"detail": "This code is invalid or has expired."}, status=status.HTTP_400_BAD_REQUEST)
        if challenge.attempts >= settings.AUTH_CODE_MAX_ATTEMPTS:
            return Response({"detail": "Too many incorrect attempts. Request a new code."}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(serializer.validated_data["code"], challenge.code_hash):
            challenge.attempts += 1
            if challenge.attempts >= settings.AUTH_CODE_MAX_ATTEMPTS:
                challenge.consumed_at = now
            challenge.save(update_fields=["attempts", "consumed_at"])
            return Response({"detail": "This code is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        challenge.consumed_at = now
        challenge.save(update_fields=["consumed_at"])
        user, created = User.objects.get_or_create(
            email__iexact=challenge.email,
            defaults={"username": challenge.email, "email": challenge.email},
        )
        if created:
            user.set_unusable_password()
        if challenge.display_name and (created or not user.get_full_name().strip()):
            name_parts = challenge.display_name.split(maxsplit=1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        if created or challenge.display_name:
            user.save()

        login(request, user)
        return Response(auth_payload(user, request))


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(auth_payload(request.user, request))


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
