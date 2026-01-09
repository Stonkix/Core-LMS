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
    
    # Тесты (Quizzes)
    path('course/<int:course_id>/quiz/add/', views.create_quiz, name='create_quiz'),
    path('quiz/<int:quiz_id>/questions/', views.manage_questions, name='manage_questions'),
    path('quiz/<int:quiz_id>/questions/add/', views.add_question, name='add_question'),
    path('quiz/<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),

    path('api/courses/', views.CourseListAPI.as_view(), name='api_course_list'),
    path('api/courses/<int:pk>/', views.CourseDetailAPI.as_view(), name='api_course_detail'),
]
