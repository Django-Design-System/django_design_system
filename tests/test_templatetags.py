from unittest.mock import patch

from django.templatetags.static import static

from dj_design_system.data import ComponentMedia
from dj_design_system.services.media import get_bundle_urls
from dj_design_system.templatetags.design_components import (
    component_scripts,
    component_stylesheets,
    global_scripts,
    global_stylesheets,
)


# The registry object used inside the template tag module.
_REGISTRY = "dj_design_system.templatetags.design_components.component_registry"

# The dds_settings object used inside the template tag module.
_DDS_SETTINGS = "dj_design_system.templatetags.design_components.dds_settings"

# The webpack availability flag inside the services.media module.
_WEBPACK_FLAG = "dj_design_system.services.media._WEBPACK_AVAILABLE"

# The webpack get_files function inside the services.media module.
_WEBPACK_GET_FILES = "dj_design_system.services.media._webpack_get_files"


class TestComponentStylesheets:
    """Tests for the ``component_stylesheets`` template tag."""

    def test_empty_registry_returns_empty_string(self):
        """When no components are registered, the tag returns an empty string."""
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia()
            result = component_stylesheets()
        assert result == ""

    def test_renders_link_tag_for_css_path(self):
        """Each CSS path becomes a ``<link rel="stylesheet">`` element."""
        path = "myapp/components/button/button.css"
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia(css=[path])
            result = str(component_stylesheets())
        assert f'href="{static(path)}"' in result
        assert 'rel="stylesheet"' in result

    def test_renders_one_link_per_path(self):
        """Two distinct CSS paths produce two ``<link>`` elements."""
        paths = [
            "myapp/components/button/button.css",
            "myapp/components/card/card.css",
        ]
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia(css=paths)
            result = str(component_stylesheets())
        assert result.count("<link") == 2

    def test_deduplicates_shared_css_paths(self):
        """A CSS path shared by two components appears only once in the output."""
        shared = "myapp/components/base/base.css"
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia(
                css=[shared, "myapp/components/a/a.css", "myapp/components/b/b.css"]
            )
            result = str(component_stylesheets())
        assert result.count(static(shared)) == 1

    def test_no_script_tags_rendered(self):
        """``component_stylesheets`` must not emit any ``<script>`` elements."""
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia(
                css=["myapp/components/button/button.css"]
            )
            result = str(component_stylesheets())
        assert "<script" not in result

    def test_component_with_only_js_returns_empty_string(self):
        """When a component has JS but no CSS, the tag returns an empty string."""
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia(
                js=["myapp/components/button/button.js"]
            )
            result = component_stylesheets()
        assert result == ""


class TestComponentScripts:
    """Tests for the ``component_scripts`` template tag."""

    def test_empty_registry_returns_empty_string(self):
        """When no components are registered, the tag returns an empty string."""
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia()
            result = component_scripts()
        assert result == ""

    def test_renders_script_tag_for_js_path(self):
        """Each JS path becomes a ``<script src="...">`` element."""
        path = "myapp/components/button/button.js"
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia(js=[path])
            result = str(component_scripts())
        assert f'src="{static(path)}"' in result
        assert "<script" in result

    def test_renders_one_script_per_path(self):
        """Two distinct JS paths produce two ``<script>`` elements."""
        paths = [
            "myapp/components/button/button.js",
            "myapp/components/card/card.js",
        ]
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia(js=paths)
            result = str(component_scripts())
        assert result.count("<script") == 2

    def test_deduplicates_shared_js_paths(self):
        """A JS path shared by two components appears only once in the output."""
        shared = "myapp/components/base/base.js"
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia(
                js=[shared, "myapp/components/a/a.js", "myapp/components/b/b.js"]
            )
            result = str(component_scripts())
        assert result.count(static(shared)) == 1

    def test_no_link_tags_rendered(self):
        """``component_scripts`` must not emit any ``<link>`` elements."""
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia(
                js=["myapp/components/button/button.js"]
            )
            result = str(component_scripts())
        assert "<link" not in result

    def test_component_with_only_css_returns_empty_string(self):
        """When a component has CSS but no JS, the tag returns an empty string."""
        with patch(_REGISTRY) as mock_registry:
            mock_registry.get_merged_media.return_value = ComponentMedia(
                css=["myapp/components/button/button.css"]
            )
            result = component_scripts()
        assert result == ""


class TestGlobalStylesheets:
    """Tests for the ``global_stylesheets`` template tag."""

    def test_empty_settings_return_empty_string(self):
        """When both GLOBAL_CSS and GLOBAL_CSS_BUNDLES are empty, returns ''."""
        with patch(_DDS_SETTINGS, GLOBAL_CSS=[], GLOBAL_CSS_BUNDLES=[]):
            result = global_stylesheets()
        assert result == ""

    def test_renders_link_tag_for_single_static_path(self):
        """A single GLOBAL_CSS path produces one ``<link rel="stylesheet">`` element."""
        path = "myapp/base.css"
        with patch(_DDS_SETTINGS, GLOBAL_CSS=[path], GLOBAL_CSS_BUNDLES=[]):
            result = str(global_stylesheets())
        assert f'href="{static(path)}"' in result
        assert 'rel="stylesheet"' in result

    def test_renders_one_link_per_static_path(self):
        """Two distinct GLOBAL_CSS paths produce two ``<link>`` elements."""
        paths = ["myapp/base.css", "myapp/theme.css"]
        with patch(_DDS_SETTINGS, GLOBAL_CSS=paths, GLOBAL_CSS_BUNDLES=[]):
            result = str(global_stylesheets())
        assert result.count("<link") == 2

    def test_no_script_tags_rendered(self):
        """``global_stylesheets`` must not emit any ``<script>`` elements."""
        with patch(_DDS_SETTINGS, GLOBAL_CSS=["myapp/base.css"], GLOBAL_CSS_BUNDLES=[]):
            result = str(global_stylesheets())
        assert "<script" not in result

    def test_renders_link_tag_from_bundle(self):
        """A GLOBAL_CSS_BUNDLES entry produces a ``<link>`` from the chunk URL."""
        chunk_url = "/static/main-abc123.css"
        with (
            patch(_WEBPACK_FLAG, True),
            patch(_WEBPACK_GET_FILES, return_value=[{"url": chunk_url}]),
            patch(_DDS_SETTINGS, GLOBAL_CSS=[], GLOBAL_CSS_BUNDLES=[("main",)]),
        ):
            result = str(global_stylesheets())
        assert f'href="{chunk_url}"' in result
        assert 'rel="stylesheet"' in result

    def test_bundle_ignored_when_webpack_unavailable(self):
        """Bundle entries are silently skipped when webpack_loader is not installed."""
        with (
            patch(_WEBPACK_FLAG, False),
            patch(_DDS_SETTINGS, GLOBAL_CSS=[], GLOBAL_CSS_BUNDLES=[("main",)]),
        ):
            result = global_stylesheets()
        assert result == ""

    def test_combines_bundle_and_static_paths(self):
        """Bundle URLs appear before static path URLs in combined output."""
        chunk_url = "/static/main-abc123.css"
        static_path = "myapp/extra.css"
        with (
            patch(_WEBPACK_FLAG, True),
            patch(_WEBPACK_GET_FILES, return_value=[{"url": chunk_url}]),
            patch(
                _DDS_SETTINGS,
                GLOBAL_CSS=[static_path],
                GLOBAL_CSS_BUNDLES=[("main",)],
            ),
        ):
            result = str(global_stylesheets())
        assert result.count("<link") == 2
        assert result.index(chunk_url) < result.index(static(static_path))


class TestGlobalScripts:
    """Tests for the ``global_scripts`` template tag."""

    def test_empty_settings_return_empty_string(self):
        """When both GLOBAL_JS and GLOBAL_JS_BUNDLES are empty, returns ''."""
        with patch(_DDS_SETTINGS, GLOBAL_JS=[], GLOBAL_JS_BUNDLES=[]):
            result = global_scripts()
        assert result == ""

    def test_renders_script_tag_for_single_static_path(self):
        """A single GLOBAL_JS path produces one ``<script src="...">`` element."""
        path = "myapp/base.js"
        with patch(_DDS_SETTINGS, GLOBAL_JS=[path], GLOBAL_JS_BUNDLES=[]):
            result = str(global_scripts())
        assert f'src="{static(path)}"' in result
        assert "<script" in result

    def test_renders_one_script_per_static_path(self):
        """Two distinct GLOBAL_JS paths produce two ``<script>`` elements."""
        paths = ["myapp/base.js", "myapp/analytics.js"]
        with patch(_DDS_SETTINGS, GLOBAL_JS=paths, GLOBAL_JS_BUNDLES=[]):
            result = str(global_scripts())
        assert result.count("<script") == 2

    def test_no_link_tags_rendered(self):
        """``global_scripts`` must not emit any ``<link>`` elements."""
        with patch(_DDS_SETTINGS, GLOBAL_JS=["myapp/base.js"], GLOBAL_JS_BUNDLES=[]):
            result = str(global_scripts())
        assert "<link" not in result

    def test_renders_script_tag_from_bundle(self):
        """A GLOBAL_JS_BUNDLES entry produces a ``<script>`` from the chunk URL."""
        chunk_url = "/static/main-abc123.js"
        with (
            patch(_WEBPACK_FLAG, True),
            patch(_WEBPACK_GET_FILES, return_value=[{"url": chunk_url}]),
            patch(_DDS_SETTINGS, GLOBAL_JS=[], GLOBAL_JS_BUNDLES=[("main",)]),
        ):
            result = str(global_scripts())
        assert f'src="{chunk_url}"' in result

    def test_bundle_ignored_when_webpack_unavailable(self):
        """Bundle entries are silently skipped when webpack_loader is not installed."""
        with (
            patch(_WEBPACK_FLAG, False),
            patch(_DDS_SETTINGS, GLOBAL_JS=[], GLOBAL_JS_BUNDLES=[("main",)]),
        ):
            result = global_scripts()
        assert result == ""

    def test_combines_bundle_and_static_paths(self):
        """Bundle URLs appear before static path URLs in combined output."""
        chunk_url = "/static/main-abc123.js"
        static_path = "myapp/extra.js"
        with (
            patch(_WEBPACK_FLAG, True),
            patch(_WEBPACK_GET_FILES, return_value=[{"url": chunk_url}]),
            patch(
                _DDS_SETTINGS,
                GLOBAL_JS=[static_path],
                GLOBAL_JS_BUNDLES=[("main",)],
            ),
        ):
            result = str(global_scripts())
        assert result.count("<script") == 2
        assert result.index(chunk_url) < result.index(static(static_path))


class TestBundleUrls:
    """Tests for the ``getget_bundle_urls`` service."""

    def test_returns_empty_list_when_webpack_unavailable(self):
        """Returns [] when _WEBPACK_AVAILABLE is False, regardless of bundles."""
        with patch(_WEBPACK_FLAG, False):
            result = get_bundle_urls([("main",)], "css")
        assert result == []

    def test_returns_empty_list_for_no_bundles(self):
        """Returns [] when the bundles list is empty, even if webpack is available."""
        with patch(_WEBPACK_FLAG, True):
            result = get_bundle_urls([], "css")
        assert result == []

    def test_returns_chunk_urls(self):
        """Returns the ``url`` field from each chunk in the bundle."""
        chunks = [{"url": "/static/a.css"}, {"url": "/static/b.css"}]
        with patch(_WEBPACK_FLAG, True), patch(_WEBPACK_GET_FILES, return_value=chunks):
            result = get_bundle_urls([("main",)], "css")
        assert result == ["/static/a.css", "/static/b.css"]

    def test_passes_default_config(self):
        """A single-element tuple uses config='DEFAULT'."""
        with (
            patch(_WEBPACK_FLAG, True),
            patch(_WEBPACK_GET_FILES, return_value=[]) as mock_get,
        ):
            get_bundle_urls([("main",)], "css")
        mock_get.assert_called_once_with("main", extension="css", config="DEFAULT")

    def test_passes_explicit_config(self):
        """A two-element tuple passes the second element as config."""
        with (
            patch(_WEBPACK_FLAG, True),
            patch(_WEBPACK_GET_FILES, return_value=[]) as mock_get,
        ):
            get_bundle_urls([("main", "MY_CONFIG")], "js")
        mock_get.assert_called_once_with("main", extension="js", config="MY_CONFIG")
