from django.db import models
from django.contrib.auth.models import User


# ==========================================
# CONVERSATION
# ==========================================

class Conversation(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="conversations"
    )

    title = models.CharField(
        max_length=200,
        default="New Chat"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.title


# ==========================================
# CHAT MESSAGE
# ==========================================

class ChatMessage(models.Model):

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    role = models.CharField(
        max_length=20
    )

    content = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


# ==========================================
# CONVERSATION INSTRUCTION
# ==========================================

class ConversationInstruction(models.Model):

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="instructions"
    )

    instruction = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.instruction[:100]