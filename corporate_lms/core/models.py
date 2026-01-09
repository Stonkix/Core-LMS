from django.db import models
from django.contrib.auth.models import AbstractUser, Group

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.username

class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='authored_courses')
    groups = models.ManyToManyField(Group, related_name='available_courses', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

class ContentBlock(models.Model):
    BLOCK_TYPES = (
        ('text', 'Текст'),
        ('file', 'Файл/Медиа'),
        ('quiz', 'Тест'),
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='blocks')
    title = models.CharField(max_length=255)
    block_type = models.CharField(max_length=10, choices=BLOCK_TYPES)
    content_text = models.TextField(blank=True, null=True)
    content_file = models.FileField(upload_to='course_contents/', blank=True, null=True)
    content_quiz = models.ForeignKey(Quiz, on_delete=models.SET_NULL, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

class StudentResult(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

class CourseCompletion(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='completions')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')