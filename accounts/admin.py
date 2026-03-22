from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.paginator import InfinitePaginator
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    model = User
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    paginator = InfinitePaginator
    show_full_result_count = False

    # Columns displayed in the admin list view
    list_display = (
        "username",
        "role",
        "phone_number",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "is_staff", "is_active", "created_at")
    search_fields = ("username", "phone_number")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    # Field layout in detail view
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Role Information"), {"fields": ("role", "phone_number")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important Dates"), {"fields": ("last_login", "created_at", "updated_at")}),
    )

    # Field layout when creating a new user
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "role",
                    "phone_number",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
