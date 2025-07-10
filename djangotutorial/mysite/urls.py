from django.contrib import admin
from django.urls import include, path
from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings

if settings.DEBUG:
    import debug_toolbar

urlpatterns = [
    path("polls/", include("polls.urls")),
    path("admin/", admin.site.urls),
    path('accounts/', include('accounts.urls')),
] +  debug_toolbar_urls()


if settings.DEBUG:
    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]