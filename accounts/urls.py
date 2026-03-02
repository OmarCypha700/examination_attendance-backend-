from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path("login/",           views.LoginView.as_view(),          name="auth-login"),
    path("logout/",          views.LogoutView.as_view(),          name="auth-logout"),
    path("token/refresh/",   TokenRefreshView.as_view(),          name="token-refresh"),
    path("me/",              views.me,                            name="auth-me"),
    path("change-password/", views.ChangePasswordView.as_view(),  name="change-password"),
    path("users/",           views.UserListCreateView.as_view(),  name="user-list"),
    path("users/<int:pk>/",  views.UserDetailView.as_view(),      name="user-detail"),
]
