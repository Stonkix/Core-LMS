from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, Course, ContentBlock, Quiz, Question, Choice, StudentResult

class CustomUserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')

# Регистрируем модели в админке
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Course)
admin.site.register(ContentBlock) # Новая модель вместо Material
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(StudentResult)