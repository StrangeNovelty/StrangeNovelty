from django.contrib.auth.views import LoginView, LogoutView

from accounts.forms import EmailAuthenticationForm


class WorkspaceLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = False
    next_page = "workspace-home"


class WorkspaceLogoutView(LogoutView):
    next_page = "login"
