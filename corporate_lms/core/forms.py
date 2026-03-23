from django import forms
from .models import Course, ContentBlock, Quiz, CustomUser, Assignment, Submission, Section
from django.contrib.auth.models import Group, Group as DGroup

MAX_AVATAR_SIZE_MB = 10


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'avatar', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
            'avatar':     forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'phone':      forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'size'):
            limit = MAX_AVATAR_SIZE_MB * 1024 * 1024
            if avatar.size > limit:
                raise forms.ValidationError(
                    f'Размер аватарки не должен превышать {MAX_AVATAR_SIZE_MB} МБ. '
                    f'Ваш файл: {avatar.size / 1024 / 1024:.1f} МБ.'
                )
        return avatar


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'groups',
                  'available_from', 'available_until',
                  'allow_self_enroll', 'access_code']
        widgets = {
            'title':           forms.TextInput(attrs={'class': 'form-control'}),
            'description':     forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'groups':          forms.SelectMultiple(attrs={'class': 'form-select'}),
            'available_from':  forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'),
            'available_until': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'),
            'access_code':     forms.TextInput(attrs={
                'class': 'form-control font-monospace',
                'placeholder': 'Введите или сгенерируйте код',
            }),
        }
        labels = {
            'available_from':    'Дата открытия',
            'available_until':   'Дата закрытия',
            'allow_self_enroll': 'Разрешить подключение по коду',
            'access_code':       'Код доступа',
        }


class EnrollForm(forms.Form):
    access_code = forms.CharField(
        label='Код доступа',
        max_length=32,
        widget=forms.TextInput(attrs={
            'class': 'form-control font-monospace text-center',
            'placeholder': 'Введите код курса...',
            'autocomplete': 'off',
        })
    )


class ContentBlockForm(forms.ModelForm):
    class Meta:
        model = ContentBlock
        fields = ['title', 'block_type', 'content_text', 'content_file', 'content_quiz']
        widgets = {
            'title':        forms.TextInput(attrs={'class': 'form-control'}),
            'block_type':   forms.Select(attrs={'class': 'form-select'}),
            'content_text': forms.Textarea(attrs={'class': 'form-control'}),
            'content_file': forms.FileInput(attrs={'class': 'form-control'}),
            'content_quiz': forms.Select(attrs={'class': 'form-select'}),
        }


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'max_attempts', 'shuffle_questions',
                  'time_limit_minutes',
                  'available_from', 'available_until']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'max_attempts': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0',
                'placeholder': '0 — без ограничений',
            }),
            'time_limit_minutes': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '1',
            }),
            'available_from':  forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'),
            'available_until': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'),
        }
        labels = {
            'max_attempts':       'Максимум попыток',
            'shuffle_questions':  'Перемешивать вопросы',
            'time_limit_minutes': 'Ограничение времени (мин)',
            'available_from':     'Дата открытия теста',
            'available_until':    'Дата закрытия теста',
        }
        help_texts = {
            'max_attempts':       '0 — неограниченное количество попыток.',
            'shuffle_questions':  'Каждый студент получит вопросы в случайном порядке.',
            'time_limit_minutes': 'Пусто — тест без ограничения времени.',
            'available_from':     'Пусто — тест доступен сразу.',
            'available_until':    'Пусто — тест без дедлайна.',
        }


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['description', 'max_score', 'deadline']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                  'placeholder': 'Опишите задание подробно...'}),
            'max_score':   forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'deadline':    forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'},
                                               format='%Y-%m-%dT%H:%M'),
        }
        labels = {
            'description': 'Описание задания',
            'max_score':   'Максимальный балл',
            'deadline':    'Срок сдачи',
        }


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['text', 'file']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 5,
                                          'placeholder': 'Ваш ответ на задание...'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'text': 'Текст ответа',
            'file': 'Прикрепить файл',
        }


class GradeSubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['score', 'feedback']
        widgets = {
            'score':    forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                              'placeholder': 'Комментарий для студента...'}),
        }
        labels = {
            'score':    'Оценка',
            'feedback': 'Комментарий преподавателя',
        }


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название урока...',
            }),
        }


class AdminUserCreateForm(forms.ModelForm):
    raw_password = forms.CharField(
        label='Пароль', required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите вручную или нажмите «Сгенерировать»',
            'id': 'id_raw_password', 'autocomplete': 'off',
        })
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=DGroup.objects.all(), required=False,
        label='Группы', widget=forms.CheckboxSelectMultiple(),
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'is_staff']
        widgets = {
            'username':   forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
            'role':       forms.Select(attrs={'class': 'form-select'}),
        }


class AdminUserEditForm(forms.ModelForm):
    new_password = forms.CharField(
        label='Новый пароль', required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Оставьте пустым, чтобы не менять',
            'id': 'id_raw_password', 'autocomplete': 'off',
        })
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=DGroup.objects.all(), required=False,
        label='Группы', widget=forms.CheckboxSelectMultiple(),
    )

    class Meta:
        model = CustomUser
        # groups намеренно НЕ в fields — управляем вручную через cleaned_data
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'is_staff']
        widgets = {
            'username':   forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
            'role':       forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Подставляем текущие группы пользователя как начальное значение
        if self.instance and self.instance.pk:
            self.fields['groups'].initial = self.instance.groups.values_list('pk', flat=True)