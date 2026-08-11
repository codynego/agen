from __future__ import annotations

from datetime import timedelta
import hashlib
import io
import re
import uuid

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .conversation_crypto import decrypt_message, encrypt_message
from .llm import get_model_router
from .managed_agents import audit
from .models import Agent, GuestAgentMessage, PublicAgentProfile
from .public_agent_serializers import (
    GuestChatInputSerializer,
    PublicCatalogSerializer,
    PublicProfileInputSerializer,
    PublicProfileSettingsSerializer,
)


def owner_business_agent(user, agent_id):
    return get_object_or_404(Agent, owner=user, kind=Agent.Kind.BUSINESS, agent_id=agent_id)


def published_agent(handle):
    return get_object_or_404(
        Agent.objects.select_related("public_profile", "managed_profile"),
        network_handle=handle,
        kind=Agent.Kind.BUSINESS,
        status=Agent.Status.ACTIVE,
        verified=True,
        public_profile__visibility__in=[PublicAgentProfile.Visibility.PUBLIC, PublicAgentProfile.Visibility.UNLISTED],
    )


def public_payload(agent):
    profile = agent.public_profile
    completed_tasks = agent.trust_events.filter(category="task_completed", outcome="positive").count()
    catalog = agent.catalog_items.filter(active=True, published=True) if profile.show_catalog else agent.catalog_items.none()
    verification_level = getattr(getattr(agent, "managed_profile", None), "verification_level", "business")
    return {
        "agent_id": agent.agent_id,
        "network_handle": agent.network_handle,
        "name": agent.name,
        "company_name": agent.company_name,
        "category": agent.category,
        "tagline": profile.tagline,
        "description": profile.public_description or agent.summary,
        "logo_url": profile.logo_url,
        "cover_url": profile.cover_url,
        "website_url": profile.website_url,
        "social_links": profile.social_links,
        "capabilities": [value for value in profile.published_capabilities if value in agent.capabilities],
        "languages": profile.languages,
        "location": profile.public_location,
        "online": agent.online,
        "trust_score": agent.trust_score,
        "trust_level": agent.trust_level,
        "verification_level": verification_level,
        "identity_verified_at": agent.identity_verified_at,
        "completed_tasks": completed_tasks,
        "public_chat_enabled": profile.public_chat_enabled,
        "catalog": PublicCatalogSerializer(catalog, many=True).data,
        "canonical_url": f"{settings.FRONTEND_PUBLIC_URL}/agents/{agent.network_handle}",
    }


class OwnerPublicProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id):
        agent = owner_business_agent(request.user, agent_id)
        profile, _ = PublicAgentProfile.objects.get_or_create(agent=agent)
        return Response(PublicProfileSettingsSerializer(profile).data)

    @transaction.atomic
    def patch(self, request, agent_id):
        agent = owner_business_agent(request.user, agent_id)
        profile, _ = PublicAgentProfile.objects.get_or_create(agent=agent)
        serializer = PublicProfileInputSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        requested_visibility = serializer.validated_data.get("visibility", profile.visibility)
        if requested_visibility != PublicAgentProfile.Visibility.PRIVATE:
            blockers = PublicProfileSettingsSerializer(profile).data["publish_blockers"]
            if blockers:
                return Response({"visibility": blockers}, status=status.HTTP_400_BAD_REQUEST)
        source_ids = serializer.validated_data.pop("published_source_ids", None)
        item_ids = serializer.validated_data.pop("published_item_ids", None)
        requested_capabilities = serializer.validated_data.get("published_capabilities")
        if requested_capabilities is not None and not set(requested_capabilities).issubset(agent.capabilities):
            return Response({"published_capabilities": ["Only configured capabilities can be published."]}, status=status.HTTP_400_BAD_REQUEST)
        profile = serializer.save()
        if source_ids is not None:
            agent.knowledge_sources.update(published=False)
            agent.knowledge_sources.filter(source_id__in=source_ids).update(published=True)
        if item_ids is not None:
            agent.catalog_items.update(published=False)
            agent.catalog_items.filter(item_id__in=item_ids).update(published=True)
        audit(agent, request.user, "public_profile_updated", f"Visibility: {profile.visibility}")
        return Response(PublicProfileSettingsSerializer(profile).data)


class PublicAgentProfileView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, network_handle):
        return Response(public_payload(published_agent(network_handle)))


class PublicAgentManifestView(PublicAgentProfileView):
    def get(self, request, network_handle):
        agent = published_agent(network_handle)
        data = public_payload(agent)
        return Response({
            "schema": "https://agen.network/schemas/agent-manifest-v1.json",
            "protocol": "agen-v1",
            "agent_id": data["agent_id"],
            "network_handle": data["network_handle"],
            "name": data["name"],
            "verification_level": data["verification_level"],
            "trust_score": data["trust_score"],
            "capabilities": data["capabilities"],
            "public_profile": data["canonical_url"],
            "chat_available": data["public_chat_enabled"],
        })


class PublicAgentQrView(PublicAgentProfileView):
    def get(self, request, network_handle):
        agent = published_agent(network_handle)
        url = f"{settings.FRONTEND_PUBLIC_URL}/agents/{agent.network_handle}"
        qr = qrcode.QRCode(version=None, box_size=8, border=3)
        qr.add_data(url)
        qr.make(fit=True)
        output = io.BytesIO()
        qr.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(output)
        return HttpResponse(output.getvalue(), content_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


def request_ip_hash(request):
    value = request.META.get("REMOTE_ADDR", "unknown")
    return hashlib.sha256(f"{settings.SECRET_KEY}:{value}".encode()).hexdigest()


def guest_response(agent, prompt):
    words = {word for word in re.findall(r"[a-z0-9]+", prompt.lower()) if len(word) > 2}
    matches = []
    for source in agent.knowledge_sources.filter(active=True, published=True):
        content = decrypt_message(source.content_ciphertext)
        score = len(words & set(re.findall(r"[a-z0-9]+", f"{source.title} {content}".lower())))
        if score:
            matches.append((score, source.title, content))
    if agent.public_profile.show_catalog:
        for item in agent.catalog_items.filter(active=True, published=True):
            score = len(words & set(re.findall(r"[a-z0-9]+", f"{item.name} {item.description} {item.sku}".lower())))
            if score:
                price = f"{item.currency} {item.price}" if item.price is not None else "Price on request"
                matches.append((score, item.name, f"{item.description} {price}. Availability: {item.availability}."))
    matches.sort(reverse=True, key=lambda item: item[0])
    published_context = [{"title": title, "content": content} for _, title, content in matches[:3]]
    managed_profile = getattr(agent, "managed_profile", None)
    generated = get_model_router().generate_business_reply(
        prompt,
        {
            "name": agent.name,
            "company_name": agent.company_name,
            "category": agent.category,
            "tone": getattr(managed_profile, "tone", "Helpful and concise"),
        },
        published_context,
    )
    if generated:
        return generated, [item["title"] for item in published_context]
    if not matches:
        business_name = agent.company_name or agent.name
        return (
            f"I don't have enough information from **{business_name}** to answer that confidently yet. "
            "Could you share a little more detail or try asking in a different way? If it's account-specific, "
            "the business contact links on this page are the quickest way to reach a person."
        ), []
    context = "\n".join(f"- **{title}:** {content}" for _, title, content in matches[:3])
    return f"Here's what I can confirm from **{agent.company_name or agent.name}**:\n\n{context}\n\nIs there anything specific you'd like me to clarify?", [title for _, title, _ in matches[:3]]


class PublicAgentGuestChatView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, network_handle):
        agent = published_agent(network_handle)
        profile = agent.public_profile
        if not profile.public_chat_enabled:
            return Response({"detail": "Public chat is not enabled for this agent."}, status=status.HTTP_403_FORBIDDEN)
        serializer = GuestChatInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip_hash = request_ip_hash(request)
        since = timezone.now() - timedelta(days=1)
        if GuestAgentMessage.objects.filter(agent=agent, ip_hash=ip_hash, created_at__gte=since).count() >= profile.guest_daily_limit:
            return Response({"detail": "This agent's guest message limit has been reached. Try again later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        prompt = serializer.validated_data["message"].strip()
        response_text, sources = guest_response(agent, prompt)
        session_id = serializer.validated_data.get("session_id") or uuid.uuid4()
        message = GuestAgentMessage.objects.create(
            agent=agent,
            session_id=session_id,
            ip_hash=ip_hash,
            prompt_ciphertext=encrypt_message(prompt),
            response_ciphertext=encrypt_message(response_text),
            matched_sources=sources,
        )
        return Response({
            "message_id": message.message_id,
            "session_id": session_id,
            "response": response_text,
            "matched_sources": sources,
        }, status=status.HTTP_201_CREATED)
