from django.contrib import admin

from .models import Conversation, ChatMessage


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "title",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "created_at",
        "updated_at",
    )

    search_fields = (
        "user__username",
        "title",
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "conversation",
        "role",
        "created_at",
    )

    list_filter = (
        "role",
        "created_at",
    )

    search_fields = (
        "content",
        "conversation__user__username",
    )