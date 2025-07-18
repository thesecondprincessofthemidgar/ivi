from django.urls import path, re_path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.search, name='search'),
    path('clear/', views.clear, name='clear'),
    path('suggestions/', views.suggestions, name='suggestions'),
    re_path(r'^media-proxy/(?P<path>.+)$', views.media_proxy, name='media_proxy'),
]
