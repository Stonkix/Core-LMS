import random
import secrets
import string
import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone

from .models import (Course, ContentBlock, Quiz, Question, Choice,
                     StudentResult, CourseCompletion, CustomUser,
                     Assignment, Submission, Section)
from .forms import (CourseForm, ContentBlockForm, QuizForm, UserProfileForm,
                    AssignmentForm, SubmissionForm, GradeSubmissionForm, SectionForm)
from rest_framework import generics
from .serializers import CourseSerializer


# ---------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ---------------------------------------------------------------

def is_teacher(user):
    return user.is_authenticated and user.role == 'teacher'

def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ---------------------------------------------------------------
# ОБЩИЕ СТРАНИЦЫ
# ---------------------------------------------------------------

@login_required
def dashboard(request):
    if request.user.role == 'teacher':
        courses = Course.objects.filter(author=request.user)

        # Все работы ожидающие проверки по курсам этого преподавателя
        pending_submissions = Submission.objects.filter(
            status='submitted',
            assignment__block__course__author=request.user
        ).select_related(
            'student', 'assignment__block__course', 'assignment__block'
        ).order_by('-submitted_at')

        return render(request, 'core/dashboard.html', {
            'courses': courses,
            'pending_submissions': pending_submissions,
        })
    else:
        all_available_courses = Course.objects.filter(
            groups__in=request.user.groups.all()).distinct()
        completed_course_ids = CourseCompletion.objects.filter(
            student=request.user).values_list('course_id', flat=True)
        completed_courses = all_available_courses.filter(id__in=completed_course_ids)
        active_courses = all_available_courses.exclude(id__in=completed_course_ids)

        # Прогресс по каждому активному курсу
        course_progress = {}
        passed_quiz_ids = set(StudentResult.objects.filter(
            student=request.user
        ).values_list('quiz_id', flat=True).distinct())

        graded_assignment_ids = set(Submission.objects.filter(
            student=request.user, status='graded'
        ).values_list('assignment__block__course_id', flat=True))

        for course in active_courses:
            blocks = course.blocks.all()
            quiz_ids = list(blocks.filter(block_type='quiz')
                           .values_list('content_quiz_id', flat=True))
            assignment_blocks = list(blocks.filter(block_type='assignment'))

            total = len(quiz_ids) + len(assignment_blocks)
            if total == 0:
                pct = 0
            else:
                done = sum(1 for qid in quiz_ids if qid in passed_quiz_ids)
                done += sum(
                    1 for b in assignment_blocks
                    if Submission.objects.filter(
                        student=request.user,
                        assignment__block=b,
                        status='graded'
                    ).exists()
                )
                pct = int((done / total) * 100)

            course_progress[course.id] = pct

        return render(request, 'core/dashboard.html', {
            'active_courses': active_courses,
            'completed_courses': completed_courses,
            'course_progress': course_progress,
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

    results = StudentResult.objects.filter(
        student=request.user).select_related('quiz', 'quiz__course')
    completions = CourseCompletion.objects.filter(
        student=request.user).select_related('course')

    context = {
        'form': UserProfileForm(instance=request.user),
        'pw_form': PasswordChangeForm(request.user),
        'results': results,
        'completions': completions,
    }
    return render(request, 'core/profile.html', context)


# ---------------------------------------------------------------
# КУРСЫ
# ---------------------------------------------------------------

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
    sections = course.sections.prefetch_related('blocks').all()
    # Блоки без урока
    loose_blocks = course.blocks.filter(section=None).order_by('order')
    quizzes = Quiz.objects.filter(course=course)
    return render(request, 'core/course_builder.html', {
        'course': course,
        'sections': sections,
        'loose_blocks': loose_blocks,
        'quizzes': quizzes,
        'form': ContentBlockForm(),
        'section_form': SectionForm(),
    })


# ---------------------------------------------------------------
# БЛОКИ
# ---------------------------------------------------------------

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
            # Привязываем к уроку если передан section_id
            section_id = request.POST.get('section_id')
            if section_id:
                try:
                    block.section = Section.objects.get(id=section_id, course=course)
                except Section.DoesNotExist:
                    pass
            block.save()
            if block.block_type == 'assignment':
                Assignment.objects.get_or_create(block=block)
        else:
            sections = course.sections.prefetch_related('blocks').all()
            loose_blocks = course.blocks.filter(section=None).order_by('order')
            quizzes = Quiz.objects.filter(course=course)
            return render(request, 'core/course_builder.html', {
                'course': course, 'sections': sections,
                'loose_blocks': loose_blocks,
                'quizzes': quizzes, 'form': form,
                'section_form': SectionForm(), 'show_modal': True,
            })
    return redirect('course_builder', course_id=course.id)


@login_required
@user_passes_test(is_teacher)
def add_section(request, course_id):
    course = get_object_or_404(Course, id=course_id, author=request.user)
    if request.method == 'POST':
        form = SectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.course = course
            section.order = course.sections.count()
            section.save()
    return redirect('course_builder', course_id=course.id)


@login_required
@user_passes_test(is_teacher)
def delete_section(request, section_id):
    section = get_object_or_404(Section, id=section_id, course__author=request.user)
    course_id = section.course_id
    if request.method == 'POST':
        # Блоки раздела открепляем (не удаляем)
        section.blocks.update(section=None)
        section.delete()
    return redirect('course_builder', course_id=course_id)


@login_required
@user_passes_test(is_teacher)
def edit_section(request, section_id):
    """Страница редактирования раздела — заголовок + блоки"""
    section = get_object_or_404(
        Section.objects.select_related('course').prefetch_related('blocks'),
        id=section_id,
        course__author=request.user,
    )
    course = section.course
    quizzes = Quiz.objects.filter(course=course)

    if request.method == 'POST' and 'rename' in request.POST:
        new_title = request.POST.get('title', '').strip()
        if new_title:
            section.title = new_title
            section.save()
        return redirect('edit_section', section_id=section.id)

    return render(request, 'core/edit_section.html', {
        'section': section,
        'course': course,
        'quizzes': quizzes,
        'blocks': section.blocks.order_by('order'),
    })


@login_required
@user_passes_test(is_teacher)
def reorder_sections(request, course_id):
    import json
    course = get_object_or_404(Course, id=course_id, author=request.user)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ids = [int(x) for x in data.get('order', [])]
            for order, lid in enumerate(ids):
                Section.objects.filter(id=lid, course=course).update(order=order)
            return JsonResponse({'ok': True})
        except Exception:
            return JsonResponse({'ok': False}, status=400)
    return JsonResponse({'ok': False}, status=405)


@login_required
@user_passes_test(is_teacher)
def move_block(request, course_id):
    """AJAX — переместить блок в другой раздел (или убрать из раздела)"""
    import json
    course = get_object_or_404(Course, id=course_id, author=request.user)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            block_id = int(data.get('block_id'))
            section_id = data.get('section_id')  # None = без раздела

            block = get_object_or_404(ContentBlock, id=block_id, course=course)

            if section_id:
                section = get_object_or_404(Section, id=int(section_id), course=course)
                block.section = section
            else:
                block.section = None

            block.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({'ok': False}, status=405)


@login_required
@user_passes_test(is_teacher)
def reorder_blocks(request, course_id):
    """AJAX — сохранить новый порядок блоков"""
    import json
    course = get_object_or_404(Course, id=course_id, author=request.user)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ids = [int(x) for x in data.get('order', [])]
            for order, bid in enumerate(ids):
                ContentBlock.objects.filter(id=bid, course=course).update(order=order)
            return JsonResponse({'ok': True})
        except Exception:
            return JsonResponse({'ok': False}, status=400)
    return JsonResponse({'ok': False}, status=405)


@login_required
@user_passes_test(is_teacher)
def delete_block(request, block_id):
    block = get_object_or_404(ContentBlock, id=block_id, course__author=request.user)
    course_id = block.course.id
    if request.method == 'POST':
        block.delete()
    return redirect('course_builder', course_id=course_id)


# ---------------------------------------------------------------
# ТЕСТЫ
# ---------------------------------------------------------------

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
    return render(request, 'core/manage_questions.html', {
        'quiz': quiz, 'questions': questions,
    })


@login_required
@user_passes_test(is_teacher)
def add_question(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, course__author=request.user)
    if request.method == 'POST':
        question_text = request.POST.get('question_text', '').strip()

        if question_text:
            # Сначала собираем варианты чтобы понять сколько правильных
            choices_data = []
            i = 1
            while True:
                choice_text = request.POST.get(f'choice_text_{i}', '').strip()
                if not choice_text:
                    break
                is_correct = request.POST.get(f'choice_correct_{i}') == '1'
                choices_data.append({'text': choice_text, 'is_correct': is_correct})
                i += 1

            # Автоматически определяем тип по количеству правильных ответов
            correct_count = sum(1 for c in choices_data if c['is_correct'])
            is_multiple = correct_count > 1

            question = Question.objects.create(
                quiz=quiz, text=question_text, is_multiple=is_multiple)

            for c in choices_data:
                Choice.objects.create(
                    question=question, text=c['text'], is_correct=c['is_correct'])

    return redirect('manage_questions', quiz_id=quiz.id)


@login_required
@user_passes_test(is_teacher)
def reorder_questions(request, quiz_id):
    """AJAX — сохранить новый порядок вопросов"""
    import json
    quiz = get_object_or_404(Quiz, id=quiz_id, course__author=request.user)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ids = [int(x) for x in data.get('order', [])]
            for order, qid in enumerate(ids):
                Question.objects.filter(id=qid, quiz=quiz).update(order=order)
            return JsonResponse({'ok': True})
        except Exception:
            return JsonResponse({'ok': False}, status=400)
    return JsonResponse({'ok': False}, status=405)


@login_required
@user_passes_test(is_teacher)
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id,
                                  quiz__course__author=request.user)
    quiz_id = question.quiz.id
    if request.method == 'POST':
        question.delete()
    return redirect('manage_questions', quiz_id=quiz_id)


@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Проверка дат теста
    if not quiz.is_open():
        from django.utils import timezone
        now = timezone.now()
        return render(request, 'core/quiz_closed.html', {
            'quiz': quiz,
            'not_yet': quiz.available_from and now < quiz.available_from,
            'expired': quiz.available_until and now > quiz.available_until,
        })

    attempts_used = StudentResult.objects.filter(
        student=request.user, quiz=quiz).count()

    blocked = quiz.max_attempts > 0 and attempts_used >= quiz.max_attempts
    attempts_left = None
    if quiz.max_attempts > 0:
        attempts_left = max(0, quiz.max_attempts - attempts_used)

    questions = list(quiz.questions.prefetch_related('choices').all())

    if request.method == 'POST':
        if blocked:
            return redirect('dashboard')

        score = 0
        max_score = len(questions)

        for q in questions:
            correct_ids = set(
                q.choices.filter(is_correct=True).values_list('id', flat=True))

            if q.is_multiple:
                # Множественный выбор — получаем список
                selected = set(
                    int(x) for x in request.POST.getlist(f'question_{q.id}')
                    if x.isdigit()
                )
                # Засчитываем только если выбраны все верные и только они
                if selected == correct_ids:
                    score += 1
            else:
                ans = request.POST.get(f'question_{q.id}')
                if ans and ans.isdigit():
                    if int(ans) in correct_ids:
                        score += 1

        StudentResult.objects.create(
            student=request.user, quiz=quiz,
            score=score, max_score=max_score)

        block = ContentBlock.objects.filter(content_quiz=quiz).first()
        if block:
            return redirect('course_detail', course_id=block.course.id)
        return redirect('dashboard')

    # GET
    if quiz.shuffle_questions:
        random.shuffle(questions)

    for q in questions:
        q.shuffled_choices = list(q.choices.all())
        random.shuffle(q.shuffled_choices)

    best_result = StudentResult.objects.filter(
        student=request.user, quiz=quiz).order_by('-score').first()

    return render(request, 'core/take_quiz.html', {
        'quiz': quiz,
        'questions': questions,
        'blocked': blocked,
        'attempts_used': attempts_used,
        'attempts_left': attempts_left,
        'best_result': best_result,
    })


# ---------------------------------------------------------------
# ЗАДАНИЯ
# ---------------------------------------------------------------

@login_required
@user_passes_test(is_teacher)
def edit_assignment(request, block_id):
    """Преподаватель редактирует описание задания"""
    block = get_object_or_404(
        ContentBlock.objects.select_related('course'),
        id=block_id,
        course__author=request.user,
    )
    course = block.course
    assignment, _ = Assignment.objects.get_or_create(block=block)

    if request.method == 'POST':
        form = AssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            return redirect('course_builder', course_id=course.id)
    else:
        form = AssignmentForm(instance=assignment)

    return render(request, 'core/assignment_form.html', {
        'form': form,
        'block': block,
        'assignment': assignment,
        'course': course,
    })


@login_required
@user_passes_test(is_teacher)
def review_submissions(request, assignment_id):
    """Преподаватель смотрит все сданные работы"""
    assignment = get_object_or_404(
        Assignment, id=assignment_id, block__course__author=request.user)
    submissions = assignment.submissions.select_related('student').order_by('-submitted_at')

    return render(request, 'core/review_submissions.html', {
        'assignment': assignment,
        'submissions': submissions,
    })


@login_required
@user_passes_test(is_teacher)
def grade_submission(request, submission_id):
    """Преподаватель оценивает конкретную работу"""
    submission = get_object_or_404(
        Submission, id=submission_id,
        assignment__block__course__author=request.user)

    if request.method == 'POST':
        form = GradeSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.status = 'graded'
            sub.graded_at = timezone.now()
            sub.save()
            messages.success(request, f'Работа {submission.student.username} оценена.')
            return redirect('review_submissions',
                            assignment_id=submission.assignment.id)
    else:
        form = GradeSubmissionForm(instance=submission)

    return render(request, 'core/grade_submission.html', {
        'form': form, 'submission': submission,
    })


@login_required
def submit_assignment(request, assignment_id):
    """Студент сдаёт работу"""
    assignment = get_object_or_404(
        Assignment.objects.select_related('block__course'),
        id=assignment_id,
    )
    course = assignment.block.course
    existing = Submission.objects.filter(
        assignment=assignment, student=request.user).first()

    if request.method == 'POST':
        if existing:
            form = SubmissionForm(request.POST, request.FILES, instance=existing)
        else:
            form = SubmissionForm(request.POST, request.FILES)

        if form.is_valid():
            from django.utils import timezone
            sub = form.save(commit=False)
            sub.assignment = assignment
            sub.student = request.user
            sub.status = 'submitted'
            sub.score = None
            sub.graded_at = None
            # Проверяем дедлайн задания
            if assignment.deadline and timezone.now() > assignment.deadline:
                sub.is_late = True
            else:
                sub.is_late = False
            sub.save()
            messages.success(request, 'Задание отправлено на проверку.')
            return redirect('course_detail', course_id=course.id)
    else:
        form = SubmissionForm(instance=existing)

    return render(request, 'core/submit_assignment.html', {
        'form': form,
        'assignment': assignment,
        'existing': existing,
        'course': course,
    })


# ---------------------------------------------------------------
# ОТОБРАЖЕНИЕ КУРСА ДЛЯ СТУДЕНТА
# ---------------------------------------------------------------

@login_required
def course_detail(request, course_id):
    if request.user.role == 'student':
        course = get_object_or_404(
            Course.objects.filter(
                id=course_id,
                groups__in=request.user.groups.all()
            ).distinct()
        )
    else:
        course = get_object_or_404(Course, id=course_id)

    # Проверка дат курса (только для студентов)
    if request.user.role == 'student' and not course.is_open():
        from django.utils import timezone
        now = timezone.now()
        return render(request, 'core/course_closed.html', {
            'course': course,
            'not_yet': course.available_from and now < course.available_from,
            'expired': course.available_until and now > course.available_until,
        })

    # Уроки и блоки без урока
    sections = course.sections.prefetch_related('blocks').all()
    loose_blocks = course.blocks.filter(section=None).order_by('order')
    all_blocks = course.blocks.all().order_by('order')

    quiz_ids = all_blocks.filter(block_type='quiz').values_list('content_quiz_id', flat=True)
    quizzes_to_pass = Quiz.objects.filter(id__in=quiz_ids)

    passed_quiz_ids = list(StudentResult.objects.filter(
        student=request.user, quiz__in=quizzes_to_pass
    ).values_list('quiz_id', flat=True).distinct())

    attempts_by_quiz = {}
    for quiz in quizzes_to_pass:
        used = StudentResult.objects.filter(student=request.user, quiz=quiz).count()
        attempts_by_quiz[quiz.id] = {
            'used': used,
            'max': quiz.max_attempts,
            'blocked': quiz.max_attempts > 0 and used >= quiz.max_attempts,
            'left': max(0, quiz.max_attempts - used) if quiz.max_attempts > 0 else None,
        }

    # Данные по заданиям
    submissions_by_assignment = {}
    for block in all_blocks.filter(block_type='assignment'):
        try:
            assignment = block.assignment
            sub = Submission.objects.filter(
                assignment=assignment, student=request.user).first()
            submissions_by_assignment[assignment.id] = sub
        except Assignment.DoesNotExist:
            pass

    # Прогресс по урокам
    section_progress = {}
    for section in sections:
        lesson_blocks = section.blocks.all()
        total = lesson_blocks.count()
        done = 0
        for b in lesson_blocks:
            if b.block_type == 'quiz' and b.content_quiz_id in passed_quiz_ids:
                done += 1
            elif b.block_type == 'assignment':
                try:
                    sub = submissions_by_assignment.get(b.assignment.id)
                    if sub and sub.status == 'graded':
                        done += 1
                except Exception:
                    pass
            elif b.block_type in ('text', 'file'):
                done += 1  # текст и файл считаем просмотренными
        pct = int((done / total) * 100) if total > 0 else 0
        section_progress[section.id] = {'done': done, 'total': total, 'pct': pct}

    # Общий прогресс курса
    total_quizzes = len(quizzes_to_pass)
    passed_count = len(passed_quiz_ids)
    all_quizzes_passed = total_quizzes <= passed_count

    # Процент выполнения курса (квизы + задания)
    assignment_blocks = list(all_blocks.filter(block_type='assignment'))
    total_items = total_quizzes + len(assignment_blocks)
    done_items = passed_count
    for b in assignment_blocks:
        try:
            sub = submissions_by_assignment.get(b.assignment.id)
            if sub and sub.status == 'graded':
                done_items += 1
        except Exception:
            pass
    overall_pct = int((done_items / total_items) * 100) if total_items > 0 else 100

    completion = CourseCompletion.objects.filter(
        student=request.user, course=course).first()

    return render(request, 'core/course_detail.html', {
        'course': course,
        'sections': sections,
        'loose_blocks': loose_blocks,
        'all_quizzes_passed': all_quizzes_passed,
        'is_completed': completion is not None,
        'completion': completion,
        'passed_quiz_ids': passed_quiz_ids,
        'attempts_by_quiz': attempts_by_quiz,
        'submissions_by_assignment': submissions_by_assignment,
        'section_progress': section_progress,
        'overall_pct': overall_pct,
    })


@login_required
def complete_course(request, course_id):
    if request.method == 'POST':
        course = get_object_or_404(Course, id=course_id)
        quiz_ids = course.blocks.filter(
            block_type='quiz').values_list('content_quiz_id', flat=True)
        passed_count = StudentResult.objects.filter(
            student=request.user, quiz_id__in=quiz_ids
        ).values('quiz').distinct().count()
        if passed_count >= len(quiz_ids):
            CourseCompletion.objects.get_or_create(student=request.user, course=course)
    return redirect('course_detail', course_id=course_id)


# ---------------------------------------------------------------
# ADMIN PANEL
# ---------------------------------------------------------------

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_panel(request):
    groups = Group.objects.all().prefetch_related('user_set')
    users = CustomUser.objects.all().order_by('-date_joined')
    context = {
        'groups': groups,
        'users': users,
        'total_students': users.filter(role='student').count(),
        'total_teachers': users.filter(role='teacher').count(),
    }
    return render(request, 'core/admin_panel.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_create_user(request):
    from .forms import AdminUserCreateForm
    generated_password = None
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if 'generate_password' in request.POST:
            generated_password = generate_password()
            return render(request, 'core/admin_user_form.html', {
                'form': form, 'generated_password': generated_password, 'action': 'create'})
        if form.is_valid():
            user = form.save(commit=False)
            raw_password = form.cleaned_data.get('raw_password')
            if not raw_password:
                raw_password = generate_password()
                generated_password = raw_password
            user.set_password(raw_password)
            user.save()
            groups_sel = form.cleaned_data.get('groups')
            if groups_sel:
                user.groups.set(groups_sel)
            if not generated_password:
                messages.success(request, f'Пользователь {user.username} создан.')
                return redirect('admin_panel')
            return render(request, 'core/admin_user_form.html', {
                'form': form, 'generated_password': generated_password,
                'created_user': user, 'action': 'created'})
    else:
        form = AdminUserCreateForm()
    return render(request, 'core/admin_user_form.html', {
        'form': form, 'action': 'create', 'generated_password': generated_password})


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_edit_user(request, user_id):
    from .forms import AdminUserEditForm
    target_user = get_object_or_404(CustomUser, id=user_id)
    generated_password = None
    if request.method == 'POST':
        if 'generate_password' in request.POST:
            generated_password = generate_password()
            form = AdminUserEditForm(instance=target_user)
            return render(request, 'core/admin_user_form.html', {
                'form': form, 'target_user': target_user,
                'generated_password': generated_password, 'action': 'edit'})
        form = AdminUserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            user = form.save(commit=False)
            new_password = form.cleaned_data.get('new_password')
            if new_password:
                user.set_password(new_password)
            user.save()
            # Явно устанавливаем группы из формы
            groups_selected = form.cleaned_data.get('groups')
            if groups_selected is not None:
                user.groups.set(groups_selected)
            messages.success(request, f'Пользователь {user.username} обновлён.')
            return redirect('admin_panel')
    else:
        form = AdminUserEditForm(instance=target_user)
    return render(request, 'core/admin_user_form.html', {
        'form': form, 'target_user': target_user,
        'action': 'edit', 'generated_password': generated_password})


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_delete_user(request, user_id):
    target_user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        target_user.delete()
        messages.success(request, 'Пользователь удалён.')
    return redirect('admin_panel')


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_create_group(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            Group.objects.get_or_create(name=name)
            messages.success(request, f'Группа "{name}" создана.')
    return redirect('admin_panel')


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        group.delete()
        messages.success(request, 'Группа удалена.')
    return redirect('admin_panel')


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_generate_password_ajax(request):
    return JsonResponse({'password': generate_password()})


# ---------------------------------------------------------------
# REST API
# ---------------------------------------------------------------

class CourseListAPI(generics.ListCreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

class CourseDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer