from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from api_keys import services as api_keys_services
from api_keys.models import UserApiKey


class _MintApiKeyForm(forms.Form):
    """Inline form rendered on the user changelist mint-key action."""

    name = forms.CharField(
        max_length=128,
        help_text="A short label so the user (and you) can tell keys apart.",
    )


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

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "mint/<int:user_id>/",
                self.admin_site.admin_view(self.mint_for_user_view),
                name="api_keys_userapikey_mint",
            ),
        ]
        return custom + urls

    def has_add_permission(self, request):
        # Keys are always created via the mint action so the raw token is
        # surfaced exactly once. Disabling the standard add form prevents
        # a superuser from accidentally persisting an unhashable record.
        return False

    @admin.action(description="Revoke selected API keys")
    def revoke_keys(self, request, queryset):
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

    def mint_for_user_view(self, request, user_id: int):
        User = get_user_model()
        user = User.objects.get(pk=user_id)
        if request.method == "POST":
            form = _MintApiKeyForm(request.POST)
            if form.is_valid():
                result = api_keys_services.mint(user, form.cleaned_data["name"])
                messages.success(
                    request,
                    format_html(
                        "API key <strong>{}</strong> minted for {}. "
                        "<strong>Copy this token now — it will not be "
                        "shown again:</strong> "
                        '<code style="display:block;margin-top:0.5em;'
                        "padding:0.5em;background:#f5f5f5;border:1px solid "
                        '#ddd;word-break:break-all;">{}</code>',
                        result.api_key.name,
                        user.username,
                        result.raw_token,
                    ),
                )
                return redirect(reverse("admin:api_keys_userapikey_changelist"))
        else:
            form = _MintApiKeyForm()
        context = {
            **self.admin_site.each_context(request),
            "title": f"Mint API key for {user.username}",
            "user_obj": user,
            "form": form,
            "opts": self.model._meta,
        }
        return render(request, "admin/api_keys/userapikey/mint.html", context)


# Patch the existing User admin to add a "Mint API key" action.
User = get_user_model()


def _mint_api_key_action(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(
            request,
            "Select exactly one user to mint an API key for.",
            messages.ERROR,
        )
        return None
    user = queryset.get()
    return redirect(reverse("admin:api_keys_userapikey_mint", args=[user.id]))


_mint_api_key_action.short_description = "Mint API key for selected user"


# The User admin is registered by django.contrib.auth; re-register so we
# can attach the mint action without rebuilding it from scratch.
try:
    user_admin = admin.site._registry[User]
    user_admin.actions = list(user_admin.actions or []) + [_mint_api_key_action]
except KeyError:
    # User admin isn't registered yet (shouldn't happen at runtime but
    # keeps test bootstrap permissive).
    pass
