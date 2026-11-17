from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import CustomPasswordChangeView, CustomPasswordChangeDoneView
from django.urls import path
from . import views

urlpatterns = [

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('perfil/', views.perfil_view, name='perfil'),
    path('editar-dados/', views.editar_dados_view, name='editar_dados'),

    # GERENCIAL
    path('usuarios/', views.lista_usuarios_view, name='lista_usuarios'),
    path('usuarios/novo/', views.cadastrar_usuario_view, name='cadastrar_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario_view, name='editar_usuario'),
    # path('usuarios/<int:pk>/status/', views.alternar_status_usuario, name='alternar_status_usuario'),
    # path('usuarios/<int:pk>/resetar-senha/', views.resetar_senha_usuario, name='resetar_senha_usuario'),
    # path('usuarios/excluir/<int:pk>/', views.excluir_usuario, name='excluir_usuario'),





    # 🔐 Redefinição de senha (esqueceu)
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='usuarios/registration/password_reset_form.html'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='usuarios/registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='usuarios/registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='usuarios/registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    # 🧩 Alteração de senha (usuário logado)
    path(
        'password_change/',
        CustomPasswordChangeView.as_view(),
        name='password_change'
    ),

    path(
        'password_change/done/',
        CustomPasswordChangeDoneView.as_view(),
        name='password_change_done'
    ),

    
     # 🔥 CORRIGIDO AQUI
    path('usuarios/<int:pk>/status/', views.alternar_status_usuario, name='alternar_status_usuario'),
    path('usuarios/<int:pk>/resetar-senha/', views.resetar_senha_usuario, name='resetar_senha_usuario'),
    path('usuarios/excluir/<int:pk>/', views.excluir_usuario, name='excluir_usuario'),


]