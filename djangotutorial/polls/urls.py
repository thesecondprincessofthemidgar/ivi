from django.urls import path

from . import views

from django.conf import settings
from debug_toolbar.toolbar import debug_toolbar_urls

app_name = "polls"

if not settings.TESTING:
    urlpatterns = [
        *urlpatterns,
    ] + debug_toolbar_urls()
else:
    urlpatterns = [
        path("", views.IndexView.as_view(), name="index"),
        path("<int:pk>/", views.DetailView.as_view(), name="detail"),
        path("<int:pk>/results/", views.ResultsView.as_view(), name="results"),
        path("<int:question_id>/vote/", views.vote, name="vote"),
    ] + debug_toolbar_urls()
