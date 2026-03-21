
from rest_framework import serializers
from .models import Course, ContentBlock

class ContentBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentBlock
        # Мы заменяем 'content' на реальные поля из твоей модели
        fields = ['id', 'title', 'block_type', 'content_text', 'content_file', 'content_quiz', 'order']

class CourseSerializer(serializers.ModelSerializer):
    # 'blocks' должен совпадать с related_name в модели ContentBlock (у тебя это 'blocks')
    blocks = ContentBlockSerializer(many=True, read_only=True)
    author_name = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'author_name', 'blocks', 'created_at']