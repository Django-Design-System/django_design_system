from django.urls import include, path

from dj_design_system import urls as dds_urls


urlpatterns = [
    path("", include(dds_urls)),
]
