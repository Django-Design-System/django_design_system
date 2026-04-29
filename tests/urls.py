from django.urls import include, path

from dj_design_system import urls


urlpatterns = [
    path("dds/", include(urls)),
]
