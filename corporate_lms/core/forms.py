from django import forms
from .models import Course, ContentBlock, Quiz, CustomUser
from django.contrib.auth.models import Group

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'groups']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

class ContentBlockForm(forms.ModelForm):
    class Meta:
        model = ContentBlock
        fields = ['title', 'block_type', 'content_text', 'content_file', 'content_quiz']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'block_type': forms.Select(attrs={'class': 'form-select'}),
            'content_text': forms.Textarea(attrs={'class': 'form-control'}),
            'content_file': forms.FileInput(attrs={'class': 'form-control'}),
            'content_quiz': forms.Select(attrs={'class': 'form-select'}),
        }

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title'] 
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
        }