import os

from django.apps import apps
from django.contrib.staticfiles.finders import BaseFinder
from django.contrib.staticfiles.storage import FileSystemStorage


ALLOWED_EXTENSIONS = {".css", ".js"}


class ComponentsStaticFinder(BaseFinder):
    """
    A static files finder that serves CSS and JS from each installed app's
    ``components/`` directory.

    Files are served under the URL namespace
    ``{app_label}/components/{sub_path}``.  Only ``.css`` and ``.js`` files
    are exposed — Python source files, HTML templates, Markdown, and any
    other file types are never served.

    To enable, add to ``STATICFILES_FINDERS`` in your Django settings::

        STATICFILES_FINDERS = [
            ...
            "dj_design_system.finders.ComponentsStaticFinder",
        ]
    """

    def __init__(self, app_names=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Build a mapping of app_label -> (components_dir, FileSystemStorage)
        # for every installed app that has a components/ directory.
        self._storages: dict[str, tuple[str, FileSystemStorage]] = {}
        for app_config in apps.get_app_configs():
            components_dir = os.path.join(app_config.path, "components")
            if os.path.isdir(components_dir):
                storage = FileSystemStorage(location=components_dir)
                storage.prefix = f"{app_config.label}/components"
                self._storages[app_config.label] = (
                    components_dir,
                    storage,
                )

    def find(self, path: str, find_all: bool = False) -> str | list[str]:
        """
        Return the filesystem path for a static file at *path* if it exists
        and has an allowed extension, or an empty list otherwise.

        *path* must be in the form ``{app_label}/components/{sub_path}``.
        """
        # Only handle paths that follow our namespace convention.
        parts = path.split("/", 2)
        if len(parts) < 3 or parts[1] != "components":
            return []

        app_label, _, sub_path = parts[0], parts[1], parts[2]

        _, ext = os.path.splitext(sub_path)
        if ext.lower() not in ALLOWED_EXTENSIONS:
            return []

        if app_label not in self._storages:
            return []

        components_dir, _ = self._storages[app_label]
        abs_path = os.path.join(components_dir, sub_path)

        if not os.path.isfile(abs_path):
            return []

        return [abs_path] if find_all else abs_path

    def list(self, ignore_patterns):
        """
        Yield ``(path, storage)`` pairs for all ``.css`` and ``.js`` files
        found under any installed app's ``components/`` directory.

        *path* is relative to the app's ``components/`` directory; *storage*
        carries the ``{app_label}/components`` namespace in ``storage.prefix``.
        """
        for _app_label, (components_dir, storage) in self._storages.items():
            for dirpath, _dirnames, filenames in os.walk(components_dir):
                for filename in filenames:
                    _, ext = os.path.splitext(filename)
                    if ext.lower() not in ALLOWED_EXTENSIONS:
                        continue
                    abs_path = os.path.join(dirpath, filename)
                    rel_path = os.path.relpath(abs_path, components_dir)
                    yield rel_path, storage
