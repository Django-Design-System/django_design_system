from django.urls import path

from dj_design_system import views


urlpatterns = [
    path(
        "",
        views.gallery_index,
        name="gallery",
    ),
    path(
        "_canvas/",
        views.canvas_iframe_view,
        name="gallery-canvas-iframe",
    ),
    # Catch-all: resolves to folder, component, or document
    # based on the node type found in the navigation tree.
    path(
        "<str:app_label>/<path:path>/",
        views.gallery_node,
        name="gallery-node",
    ),
    # App root (no path segments after the app label)
    path(
        "<str:app_label>/",
        views.gallery_node,
        name="gallery-node-root",
    ),
]
