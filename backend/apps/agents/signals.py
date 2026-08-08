from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import TrustEvent
from .services import recalculate_trust_score


@receiver(post_save, sender=TrustEvent)
@receiver(post_delete, sender=TrustEvent)
def update_agent_trust_score(sender, instance, **kwargs):
    recalculate_trust_score(instance.subject_agent)
