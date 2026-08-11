from rest_framework import serializers

from .conversation_crypto import decrypt_message
from .models import Conversation, ConversationMessage
from .resolver_serializers import TaskSerializer


class ConversationMessageSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    task_id = serializers.UUIDField(source="task.task_id", read_only=True, allow_null=True)

    class Meta:
        model = ConversationMessage
        fields = ["message_id", "role", "sequence", "content", "task_id", "created_at"]

    def get_content(self, obj):
        return decrypt_message(obj.content_ciphertext)


class ConversationSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(read_only=True)
    latest_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "conversation_id",
            "title",
            "status",
            "retention_policy",
            "expires_at",
            "last_message_at",
            "message_count",
            "latest_message",
            "created_at",
        ]

    def get_latest_message(self, obj):
        message = next(iter(getattr(obj, "latest_messages", [])), None)
        if message is None:
            message = obj.messages.order_by("-sequence").first()
        if message is None:
            return ""
        content = decrypt_message(message.content_ciphertext)
        return content[:120]


class ConversationDetailSerializer(ConversationSerializer):
    messages = ConversationMessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = [*ConversationSerializer.Meta.fields, "messages"]


class ConversationCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, required=False, default="New conversation")
    retention_policy = serializers.ChoiceField(
        choices=Conversation.RetentionPolicy.choices,
        required=False,
        default=Conversation.RetentionPolicy.THIRTY_DAYS,
    )


class ConversationUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, required=False)
    status = serializers.ChoiceField(choices=Conversation.Status.choices, required=False)


class MessageInputSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=4000, trim_whitespace=True)

    def validate_content(self, value):
        if not value:
            raise serializers.ValidationError("Write a message for your agent.")
        return value


class ConversationSendSerializer(serializers.Serializer):
    user_message = ConversationMessageSerializer()
    agent_message = ConversationMessageSerializer()
    task = TaskSerializer()
