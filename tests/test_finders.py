import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.apps import AppConfig

from dj_design_system.finders import (
    ALLOWED_EXTENSIONS,
    ComponentsStaticFinder,
)


# The demo_components' components directory — used to construct expected paths.
DEMO_COMPONENTS_DIR = (
    Path(__file__).parent.parent / "example_project" / "demo_components" / "components"
)


@pytest.fixture()
def finder():
    """Return a ComponentsStaticFinder scoped to isolated test apps only.

    We patch ``apps.get_app_configs()`` so the finder only sees demo_components,
    preventing interference from real installed apps.
    """
    from unittest.mock import MagicMock

    from django.apps import AppConfig

    demo_config = MagicMock(spec=AppConfig)
    demo_config.label = "demo_components"
    demo_config.path = str(
        Path(__file__).parent.parent / "example_project" / "demo_components"
    )

    with patch(
        "dj_design_system.finders.apps.get_app_configs",
        return_value=[demo_config],
    ):
        yield ComponentsStaticFinder()


class TestAllowedExtensions:
    def test_css_is_allowed(self):
        assert ".css" in ALLOWED_EXTENSIONS

    def test_js_is_allowed(self):
        assert ".js" in ALLOWED_EXTENSIONS

    def test_py_is_not_allowed(self):
        assert ".py" not in ALLOWED_EXTENSIONS

    def test_md_is_not_allowed(self):
        assert ".md" not in ALLOWED_EXTENSIONS

    def test_html_is_not_allowed(self):
        assert ".html" not in ALLOWED_EXTENSIONS


class TestFind:
    def test_finds_css_file(self, finder):
        result = finder.find("demo_components/components/button/button.css")
        expected = str(DEMO_COMPONENTS_DIR / "button" / "button.css")
        assert result == expected

    def test_finds_js_file(self, finder):
        result = finder.find("demo_components/components/button/button.js")
        expected = str(DEMO_COMPONENTS_DIR / "button" / "button.js")
        assert result == expected

    def test_returns_list_when_all_true(self, finder):
        result = finder.find(
            "demo_components/components/button/button.css", find_all=True
        )
        expected = str(DEMO_COMPONENTS_DIR / "button" / "button.css")
        assert result == [expected]

    def test_rejects_python_file(self, finder):
        result = finder.find("demo_components/components/button/button.py")
        assert result == []

    def test_rejects_non_components_namespace(self, finder):
        """Paths not matching {app_label}/components/{sub_path} are ignored."""
        result = finder.find("demo_components/static/button.css")
        assert result == []

    def test_returns_none_for_unknown_app(self, finder):
        result = finder.find("unknown_app/components/button.css")
        assert result == []

    def test_returns_none_for_nonexistent_file(self, finder):
        result = finder.find("demo_components/components/nonexistent.css")
        assert result == []

    def test_finds_nested_css_file(self, finder):
        """Nested path that doesn't exist returns None."""
        result = finder.find("demo_components/components/card/nonexistent.css")
        assert result == []


class TestList:
    def test_yields_css_and_js_only(self, finder):
        paths = [path for path, _storage in finder.list(ignore_patterns=[])]
        for path in paths:
            _, ext = os.path.splitext(path)
            assert ext in ALLOWED_EXTENSIONS, (
                f"Unexpected extension in listed path: {path}"
            )

    def test_yields_button_css(self, finder):
        paths = [path for path, _storage in finder.list(ignore_patterns=[])]
        assert "button/button.css" in paths

    def test_yields_button_js(self, finder):
        paths = [path for path, _storage in finder.list(ignore_patterns=[])]
        assert "button/button.js" in paths

    def test_does_not_yield_python_files(self, finder):
        paths = [path for path, _storage in finder.list(ignore_patterns=[])]
        assert not any(p.endswith(".py") for p in paths)

    def test_storage_location_is_components_dir(self, finder):
        """The storage for each yielded file is rooted at the app's components/ dir."""
        for _path, storage in finder.list(ignore_patterns=[]):
            assert storage.location == str(DEMO_COMPONENTS_DIR)

    def test_no_storages_when_no_apps_with_components(self):
        """Finder with no apps that have a components/ dir yields nothing."""
        empty_config = MagicMock(spec=AppConfig)
        empty_config.label = "emptyapp"
        empty_config.path = "/nonexistent/path"

        with patch(
            "dj_design_system.finders.apps.get_app_configs",
            return_value=[empty_config],
        ):
            f = ComponentsStaticFinder()
            items = list(f.list(ignore_patterns=[]))
            assert items == []
