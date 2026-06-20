from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from inspection.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'real_name', 'is_staff')
    list_filter = ('role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('扩展信息', {'fields': ('role', 'real_name', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('扩展信息', {'fields': ('role', 'real_name', 'phone')}),
    )
