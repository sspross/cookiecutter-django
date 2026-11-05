from django.contrib import admin, messages
from django.db.models import QuerySet
from django.forms import ModelForm
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html

from api_keys import services as api_keys_services
from api_keys.models import UserApiKey


@admin.register(UserApiKey)
class UserApiKeyAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "name",
        "prefix",
        "created_at",
        "last_used_at",
        "revoked_at",
    )
    list_filter = ("revoked_at",)
    search_fields = ("user__username", "name", "prefix")
    readonly_fields = ("prefix", "hash", "created_at", "last_used_at", "revoked_at")
    actions = ("revoke_keys",)

    def get_fields(
        self, request: HttpRequest, obj: UserApiKey | None = None
    ) -> tuple[str, ...]:
        if obj is None:
            return ("user", "name")
        return ("user", "name", *self.readonly_fields)

    def save_model(
        self, request: HttpRequest, obj: UserApiKey, form: ModelForm, change: bool
    ) -> None:
        if change:
            super().save_model(request, obj, form, change)
            return
        # services.mint owns the prefix/hash policy, so it creates the row, not super().
        result = api_keys_services.mint(user=obj.user, name=obj.name)
        obj.pk = result.api_key.pk
        request._minted_raw_token = result.raw_token  # type: ignore[attr-defined]

    def response_add(
        self,
        request: HttpRequest,
        obj: UserApiKey,
        post_url_continue: str | None = None,
    ) -> HttpResponse:
        raw_token = getattr(request, "_minted_raw_token", None)
        if raw_token:
            messages.success(
                request,
                format_html(
                    "API key <strong>{}</strong> minted for {}. "
                    "<strong>Copy this token now — it will not be "
                    "shown again:</strong> "
                    '<code style="display:block;margin-top:0.5em;'
                    "padding:0.5em;background:#f5f5f5;border:1px solid "
                    '#ddd;word-break:break-all;">{}</code>',
                    obj.name,
                    obj.user.username,
                    raw_token,
                ),
            )
        return super().response_add(request, obj, post_url_continue)

    @admin.action(description="Revoke selected API keys")
    def revoke_keys(self, request: HttpRequest, queryset: QuerySet[UserApiKey]) -> None:
        revoked_count = 0
        for api_key in queryset:
            if api_key.revoked_at is None:
                api_keys_services.revoke(api_key)
                revoked_count += 1
        self.message_user(
            request,
            f"Revoked {revoked_count} API key(s).",
            messages.SUCCESS,
        )
