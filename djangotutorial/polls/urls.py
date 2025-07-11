from django.urls import path, re_path

from . import views

app_name = "polls"
urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("<int:pk>/", views.DetailView.as_view(), name="detail"),
    path("<int:pk>/results/", views.ResultsView.as_view(), name="results"),
    path("<int:question_id>/vote/", views.vote, name="vote"),
    path("search/", views.search, name="search"),
    re_path(r'^media-proxy/(?P<path>.+)$', views.media_proxy, name='media_proxy'),
]
