from django.contrib.auth.decorators import login_required
from django.urls import path

from testy_gitlab_runner import views

urlpatterns = [
    path("", login_required(views.ConfigView.as_view()), name="index"),
    path("tokens/", login_required(views.TokensView.as_view()), name="tokens"),
    path("runs/", login_required(views.RunsView.as_view()), name="runs"),
    path("config/<int:project_id>/", login_required(views.SaveConnectionView.as_view()), name="config"),
    path(
        "retention/<int:project_id>/",
        login_required(views.RetentionConfigView.as_view()),
        name="retention-config",
    ),
    path(
        "cleanup/<int:project_id>/",
        login_required(views.RunCleanupView.as_view()),
        name="run-cleanup",
    ),
    path("token/generate/", login_required(views.GenerateTokenView.as_view()), name="generate-token"),
    path(
        "token/<str:key>/revoke/",
        login_required(views.RevokeTokenView.as_view()),
        name="revoke-token",
    ),
    path("run/", login_required(views.RunView.as_view()), name="run"),
    path("sync/", login_required(views.SyncView.as_view()), name="sync"),
    path("api/run/", views.RunTestsAPIView.as_view(), name="api-run"),
    path(
        "api/plan/<int:plan_id>/run-status/",
        views.PlanRunStatusAPIView.as_view(),
        name="api-plan-run-status",
    ),
]
