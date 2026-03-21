from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),

    # Курсы
    path('course/create/', views.create_course, name='create_course'),
    path('course/<int:course_id>/edit/', views.edit_course, name='edit_course'),
    path('course/builder/<int:course_id>/', views.course_builder, name='course_builder'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('course/<int:course_id>/complete/', views.complete_course, name='complete_course'),

    # Блоки контента
    path('course/<int:course_id>/add_block/', views.add_block, name='add_block'),
    path('block/<int:block_id>/delete/', views.delete_block, name='delete_block'),
    path('course/<int:course_id>/reorder_blocks/', views.reorder_blocks, name='reorder_blocks'),
    path('course/<int:course_id>/move_block/', views.move_block, name='move_block'),
    path('course/<int:course_id>/section/add/', views.add_section, name='add_section'),
    path('section/<int:section_id>/delete/', views.delete_section, name='delete_section'),
    path('section/<int:section_id>/edit/', views.edit_section, name='edit_section'),
    path('course/<int:course_id>/reorder_sections/', views.reorder_sections, name='reorder_sections'),

    # Тесты
    path('course/<int:course_id>/quiz/add/', views.create_quiz, name='create_quiz'),
    path('quiz/<int:quiz_id>/questions/', views.manage_questions, name='manage_questions'),
    path('quiz/<int:quiz_id>/questions/add/', views.add_question, name='add_question'),
    path('question/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    path('quiz/<int:quiz_id>/questions/reorder/', views.reorder_questions, name='reorder_questions'),
    path('quiz/<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),

    # Задания
    path('block/<int:block_id>/assignment/edit/', views.edit_assignment, name='edit_assignment'),
    path('assignment/<int:assignment_id>/submissions/', views.review_submissions, name='review_submissions'),
    path('submission/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),
    path('assignment/<int:assignment_id>/submit/', views.submit_assignment, name='submit_assignment'),

    # REST API
    path('api/courses/', views.CourseListAPI.as_view(), name='api_course_list'),
    path('api/courses/<int:pk>/', views.CourseDetailAPI.as_view(), name='api_course_detail'),

    # Админ-панель
    path('manage/', views.admin_panel, name='admin_panel'),
    path('manage/user/create/', views.admin_create_user, name='admin_create_user'),
    path('manage/user/<int:user_id>/edit/', views.admin_edit_user, name='admin_edit_user'),
    path('manage/user/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('manage/group/create/', views.admin_create_group, name='admin_create_group'),
    path('manage/group/<int:group_id>/delete/', views.admin_delete_group, name='admin_delete_group'),
    path('manage/api/gen-password/', views.admin_generate_password_ajax, name='admin_gen_password'),
]