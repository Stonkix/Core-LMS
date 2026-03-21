from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.db.models.signals import pre_save
from django.dispatch import receiver
import os


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
    available_from = models.DateTimeField(null=True, blank=True,
        help_text='Дата открытия курса. Пусто — доступен сразу.')
    available_until = models.DateTimeField(null=True, blank=True,
        help_text='Дата закрытия курса. Пусто — бессрочно.')

    def is_open(self):
        from django.utils import timezone
        now = timezone.now()
        if self.available_from and now < self.available_from:
            return False
        if self.available_until and now > self.available_until:
            return False
        return True

    def __str__(self):
        return self.title


class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=255)
    max_attempts = models.PositiveIntegerField(
        default=0,
        help_text='0 — неограниченное количество попыток'
    )
    shuffle_questions = models.BooleanField(
        default=False,
        help_text='Перемешивать вопросы случайно для каждого студента'
    )
    available_from = models.DateTimeField(null=True, blank=True,
        help_text='Дата открытия теста. Пусто — доступен сразу.')
    available_until = models.DateTimeField(null=True, blank=True,
        help_text='Дата закрытия теста. Пусто — бессрочно.')

    def is_open(self):
        from django.utils import timezone
        now = timezone.now()
        if self.available_from and now < self.available_from:
            return False
        if self.available_until and now > self.available_until:
            return False
        return True

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    is_multiple = models.BooleanField(
        default=False,
        help_text='Несколько правильных ответов (checkbox вместо radio)'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text[:60]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)


class Section(models.Model):
    """Раздел — группа блоков внутри курса"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class ContentBlock(models.Model):
    BLOCK_TYPES = (
        ('text', 'Текст'),
        ('file', 'Файл/Медиа'),
        ('quiz', 'Тест'),
        ('assignment', 'Задание'),
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='blocks')
    section = models.ForeignKey('Section', on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='blocks')
    title = models.CharField(max_length=255)
    block_type = models.CharField(max_length=20, choices=BLOCK_TYPES)
    content_text = models.TextField(blank=True, null=True)
    content_file = models.FileField(upload_to='course_contents/', blank=True, null=True)
    content_quiz = models.ForeignKey(Quiz, on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name='blocks')
    order = models.PositiveIntegerField(default=0)


class Assignment(models.Model):
    """Задание в блоке курса"""
    block = models.OneToOneField(ContentBlock, on_delete=models.CASCADE, related_name='assignment')
    description = models.TextField(blank=True)
    max_score = models.PositiveIntegerField(default=100)
    deadline = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Задание: {self.block.title}'


class Submission(models.Model):
    """Ответ студента на задание"""
    STATUS_CHOICES = (
        ('submitted', 'На проверке'),
        ('graded', 'Проверено'),
    )
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='submissions')
    text = models.TextField(blank=True)
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    score = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    is_late = models.BooleanField(default=False,
        help_text='Помечается автоматически если сдано после дедлайна')

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f'{self.student.username} → {self.assignment}'


class StudentResult(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    max_score = models.IntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)


class CourseCompletion(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='completions')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')


@receiver(pre_save, sender=CustomUser)
def delete_old_avatar(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_user = CustomUser.objects.get(pk=instance.pk)
    except CustomUser.DoesNotExist:
        return
    old_avatar = old_user.avatar
    new_avatar = instance.avatar
    if old_avatar and old_avatar != new_avatar:
        if os.path.isfile(old_avatar.path):
            os.remove(old_avatar.path)