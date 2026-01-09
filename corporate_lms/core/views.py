import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Course, ContentBlock, Quiz, Question, Choice, StudentResult, CourseCompletion
from .forms import CourseForm, ContentBlockForm, QuizForm, UserProfileForm
from rest_framework import generics
from .serializers import CourseSerializer

from django.contrib.auth.decorators import login_required
from rest_framework import generics
from .models import Course, ContentBlock

# --- ПРОВЕРКИ ДОСТУПА ---
def is_teacher(user):
    return user.is_authenticated and user.role == 'teacher'

# --- ОБЩИЕ СТРАНИЦЫ ---
@login_required
def dashboard(request):
    if request.user.role == 'teacher':
        courses = Course.objects.filter(author=request.user)
        return render(request, 'core/dashboard.html', {'courses': courses})
    else:
        # Получаем все курсы, доступные группам студента
        all_available_courses = Course.objects.filter(groups__in=request.user.groups.all()).distinct()
        
        # Получаем ID курсов, которые студент уже завершил
        completed_course_ids = CourseCompletion.objects.filter(student=request.user).values_list('course_id', flat=True)
        
        # Разделяем курсы на две категории
        completed_courses = all_available_courses.filter(id__in=completed_course_ids)
        active_courses = all_available_courses.exclude(id__in=completed_course_ids)
        
        return render(request, 'core/dashboard.html', {
            'active_courses': active_courses,
            'completed_courses': completed_courses
        })

@login_required
def profile_view(request):
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            form = UserProfileForm(request.POST, request.FILES, instance=request.user)
            if form.is_valid():
                form.save()
                return redirect('profile')
        elif 'change_password' in request.POST:
            pw_form = PasswordChangeForm(request.user, request.POST)
            if pw_form.is_valid():
                user = pw_form.save()
                update_session_auth_hash(request, user)
                return redirect('profile')
    
    # Получаем результаты тестов и завершенные курсы для профиля
    results = StudentResult.objects.filter(student=request.user).select_related('quiz', 'quiz__course')
    completions = CourseCompletion.objects.filter(student=request.user).select_related('course')
    
    context = {
        'form': UserProfileForm(instance=request.user),
        'pw_form': PasswordChangeForm(request.user),
        'results': results,
        'completions': completions,
    }
    return render(request, 'core/profile.html', context)

# --- КУРСЫ (УПРАВЛЕНИЕ) ---
@login_required
@user_passes_test(is_teacher)
def create_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.author = request.user
            course.save()
            form.save_m2m()
            return redirect('course_builder', course_id=course.id)
    else:
        form = CourseForm()
    return render(request, 'core/course_form.html', {'form': form})

@login_required
@user_passes_test(is_teacher)
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, author=request.user)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            return redirect('course_builder', course_id=course.id)
    else:
        form = CourseForm(instance=course)
    return render(request, 'core/course_form.html', {'form': form, 'course': course})

@login_required
@user_passes_test(is_teacher)
def course_builder(request, course_id):
    course = get_object_or_404(Course, id=course_id, author=request.user)
    blocks = course.blocks.all().order_by('order')
    quizzes = Quiz.objects.filter(course=course)
    return render(request, 'core/course_builder.html', {
        'course': course, 
        'blocks': blocks,
        'quizzes': quizzes,
        'form': ContentBlockForm()
    })

# --- БЛОКИ ---
@login_required
@user_passes_test(is_teacher)
def add_block(request, course_id):
    course = get_object_or_404(Course, id=course_id, author=request.user)
    if request.method == 'POST':
        form = ContentBlockForm(request.POST, request.FILES)
        if form.is_valid():
            block = form.save(commit=False)
            block.course = course
            block.order = course.blocks.count()
            block.save()
    return redirect('course_builder', course_id=course.id)

@login_required
@user_passes_test(is_teacher)
def delete_block(request, block_id):
    block = get_object_or_404(ContentBlock, id=block_id, course__author=request.user)
    course_id = block.course.id
    if request.method == 'POST':
        block.delete()
    return redirect('course_builder', course_id=course_id)

# --- ТЕСТЫ ---
@login_required
@user_passes_test(is_teacher)
def create_quiz(request, course_id):
    course = get_object_or_404(Course, id=course_id, author=request.user)
    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.course = course
            quiz.save()
            return redirect('manage_questions', quiz_id=quiz.id)
    else:
        form = QuizForm()
    return render(request, 'core/quiz_form.html', {'form': form, 'course': course})

@login_required
@user_passes_test(is_teacher)
def manage_questions(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, course__author=request.user)
    questions = quiz.questions.all().prefetch_related('choices')
    return render(request, 'core/manage_questions.html', {'quiz': quiz, 'questions': questions})

@login_required
@user_passes_test(is_teacher)
def add_question(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, course__author=request.user)
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        correct_index = request.POST.get('correct_choice')
        
        if question_text:
            question = Question.objects.create(quiz=quiz, text=question_text)
            for i in range(1, 5):
                choice_text = request.POST.get(f'choice_{i}')
                if choice_text:
                    Choice.objects.create(
                        question=question,
                        text=choice_text,
                        is_correct=(str(i) == correct_index)
                    )
    return redirect('manage_questions', quiz_id=quiz.id)

@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = list(quiz.questions.all())
    if request.method == 'POST':
        score = 0
        for q in questions:
            ans = request.POST.get(f'question_{q.id}')
            if ans and Choice.objects.filter(id=ans, is_correct=True).exists():
                score += 1
        StudentResult.objects.create(student=request.user, quiz=quiz, score=score)
        # После теста возвращаем на страницу курса, чтобы увидеть прогресс
        block = ContentBlock.objects.filter(content_quiz=quiz).first()
        if block:
            return redirect('course_detail', course_id=block.course.id)
        return redirect('dashboard')
        
    for q in questions:
        q.shuffled_choices = list(q.choices.all())
        random.shuffle(q.shuffled_choices)
    return render(request, 'core/take_quiz.html', {'quiz': quiz, 'questions': questions})

# --- ОТОБРАЖЕНИЕ КУРСА ДЛЯ СТУДЕНТА ---
@login_required
def course_detail(request, course_id):
    if request.user.role == 'student':
        course = get_object_or_404(Course, id=course_id, groups__in=request.user.groups.all())
    else:
        course = get_object_or_404(Course, id=course_id)
        
    blocks = course.blocks.all().order_by('order')
    
    # 1. Ищем все тесты, привязанные к этому курсу через блоки
    quiz_ids = blocks.filter(block_type='quiz').values_list('content_quiz_id', flat=True)
    quizzes_to_pass = Quiz.objects.filter(id__in=quiz_ids)
    
    # 2. Проверяем пройденные тесты
    passed_quiz_ids = StudentResult.objects.filter(
        student=request.user, 
        quiz__in=quizzes_to_pass
    ).values_list('quiz_id', flat=True).distinct()

    # 3. Флаги прогресса
    all_quizzes_passed = len(quizzes_to_pass) <= len(passed_quiz_ids)
    completion = CourseCompletion.objects.filter(student=request.user, course=course).first()

    return render(request, 'core/course_detail.html', {
        'course': course,
        'blocks': blocks,
        'all_quizzes_passed': all_quizzes_passed,
        'is_completed': completion is not None,
        'completion': completion,
        'passed_quiz_ids': passed_quiz_ids
    })

@login_required
def complete_course(request, course_id):
    if request.method == 'POST':
        course = get_object_or_404(Course, id=course_id)
        
        # Проверка на стороне сервера
        quiz_ids = course.blocks.filter(block_type='quiz').values_list('content_quiz_id', flat=True)
        passed_count = StudentResult.objects.filter(
            student=request.user, 
            quiz_id__in=quiz_ids
        ).values('quiz').distinct().count()
        
        if passed_count >= len(quiz_ids):
            CourseCompletion.objects.get_or_create(student=request.user, course=course)
    
    return redirect('course_detail', course_id=course_id)


# --- НОВОЕ API VIEW ---
class CourseListAPI(generics.ListCreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

class CourseDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer