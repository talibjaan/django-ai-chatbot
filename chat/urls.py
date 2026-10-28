from django.contrib import admin
from django.urls import path 
from chat import views
urlpatterns = [
    path('', views.home , name='home'),
    path('chat/', views.chat , name='chat'),
    path('login/', views.login_view , name= 'login'),
    path('register/', views.register_view , name='register'),
    path('logout/', views.logout_view , name='logout'),
    path("conversations/",views.conversations,name="conversations"),
    path("conversations/<int:conversation_id>/",views.conversation_detail,name="conversation_detail"),
    path("conversations/<int:conversation_id>/delete/",views.delete_conversation,name="delete_conversation"),
    path("api/widget/chat/",views.widget_chat,name="widget_chat"),
]
