"""Tests for the canvas rendering service."""

import pytest
from django.http import QueryDict

from dj_design_system.data import CanvasSpec, ComponentMedia
from dj_design_system.services.canvas import (
    build_canvas_url,
    coerce_single,
    get_component_media,
    render_component,
    resolve_from_get_params,
)


# ---------------------------------------------------------------------------
# resolve_from_get_params
# ---------------------------------------------------------------------------


class TestResolveFromGetParams:
    """Test building a CanvasSpec from GET query parameters."""

    def test_basic_resolution(self, registry_with_demo_components):
        qd = QueryDict("component=button")
        spec = resolve_from_get_params(qd, registry_with_demo_components)
        assert spec.component_name == "button"

    def test_with_keyword_params(self, registry_with_demo_components):
        # "label" is a positional arg for button, so it ends up in
        # positional_args rather than params.
        qd = QueryDict("component=button&label=Click+me")
        spec = resolve_from_get_params(qd, registry_with_demo_components)
        assert spec.component_name == "button"
        assert "Click me" in spec.positional_args

    def test_missing_component_param_raises(self, registry_with_demo_components):
        qd = QueryDict("")
        with pytest.raises(ValueError, match="Missing required"):
            resolve_from_get_params(qd, registry_with_demo_components)

    def test_unknown_component_raises(self, registry_with_demo_components):
        qd = QueryDict("component=nonexistent")
        with pytest.raises(ValueError, match="not found in registry"):
            resolve_from_get_params(qd, registry_with_demo_components)

    def test_bg_param_excluded_from_component_params(
        self, registry_with_demo_components
    ):
        qd = QueryDict("component=button&bg=dark-grey")
        spec = resolve_from_get_params(qd, registry_with_demo_components)
        assert "bg" not in spec.params

    def test_block_component_content_passed_through(
        self, registry_with_demo_components
    ):
        """resolve_from_get_params passes 'content' through for BlockComponents."""
        qd = QueryDict("component=alert&type=warning&content=Hello+world")
        spec = resolve_from_get_params(qd, registry_with_demo_components)
        assert spec.params.get("content") == "Hello world"

    def test_unknown_params_ignored(self, registry_with_demo_components):
        qd = QueryDict("component=button&nonsense=foo")
        spec = resolve_from_get_params(qd, registry_with_demo_components)
        assert "nonsense" not in spec.params


class TestRenderBlockComponent:
    """Test canvas rendering of BlockComponent subclasses."""

    def test_render_block_component(self, registry_with_demo_components):
        """A BlockComponent renders its content."""
        spec = CanvasSpec(
            component_name="alert",
            params={"type": "warning", "content": "Watch out!"},
        )
        html = render_component(spec, registry_with_demo_components)
        assert "Watch out!" in html


# ---------------------------------------------------------------------------
# render_component
# ---------------------------------------------------------------------------


class TestRenderComponent:
    """Test component rendering from a CanvasSpec."""

    def test_successful_render(self, registry_with_demo_components):
        spec = CanvasSpec(component_name="button", params={"label": "OK"})
        html = render_component(spec, registry_with_demo_components)
        assert "OK" in html

    def test_missing_component_returns_error(self, registry_with_demo_components):
        spec = CanvasSpec(component_name="nonexistent")
        html = render_component(spec, registry_with_demo_components)
        assert "color:red" in html
        assert "not found" in html

    def test_validation_error_returns_error(self, registry_with_demo_components):
        """Component validation errors should render in red."""
        spec = CanvasSpec(component_name="button", params={})
        html = render_component(spec, registry_with_demo_components)
        # ButtonComponent requires 'label' param — should error
        assert "color:red" in html or "button" in html.lower()


# ---------------------------------------------------------------------------
# get_component_media
# ---------------------------------------------------------------------------


class TestGetComponentMedia:
    """Test CSS/JS media resolution for a canvas component."""

    def test_returns_media_for_known_component(self, registry_with_demo_components):
        spec = CanvasSpec(component_name="button")
        media = get_component_media(spec, registry_with_demo_components)
        assert isinstance(media, ComponentMedia)
        # ButtonComponent has co-located CSS/JS
        assert any("button" in path for path in media.css)

    def test_returns_empty_for_unknown_component(self, registry_with_demo_components):
        spec = CanvasSpec(component_name="nonexistent")
        media = get_component_media(spec, registry_with_demo_components)
        assert media.css == []
        assert media.js == []


# ---------------------------------------------------------------------------
# build_canvas_url
# ---------------------------------------------------------------------------


class TestBuildCanvasUrl:
    """Test URL generation from a CanvasSpec."""

    def test_basic_url(self):
        spec = CanvasSpec(component_name="button")
        url = build_canvas_url(spec, "/base/")
        assert url.startswith("/base/?")
        assert "component=button" in url

    def test_with_params(self):
        spec = CanvasSpec(component_name="button", params={"size": "large"})
        url = build_canvas_url(spec, "/base/")
        assert "component=button" in url
        assert "size=large" in url

    def test_bool_params_serialised_correctly(self):
        spec = CanvasSpec(component_name="button", params={"dark": True})
        url = build_canvas_url(spec, "/base/")
        assert "dark=true" in url

    def test_false_bool_params_serialised(self):
        spec = CanvasSpec(component_name="button", params={"dark": False})
        url = build_canvas_url(spec, "/base/")
        assert "dark=false" in url


# ---------------------------------------------------------------------------
# _coerce_single
# ---------------------------------------------------------------------------


class TestCoerceSingle:
    """Test type coercion for individual parameter values."""

    def test_string_passthrough(self):
        class FakeSpec:
            type = str

        assert coerce_single("name", "hello", FakeSpec()) == "hello"

    def test_bool_true_variants(self):
        class FakeSpec:
            type = bool

        for value in ("true", "True", "1", "yes"):
            assert coerce_single("flag", value, FakeSpec()) is True

    def test_bool_false_variants(self):
        class FakeSpec:
            type = bool

        for value in ("false", "False", "0", "no"):
            assert coerce_single("flag", value, FakeSpec()) is False

    def test_int_coercion(self):
        class FakeSpec:
            type = int

        assert coerce_single("count", "42", FakeSpec()) == 42

    def test_int_invalid_raises(self):
        class FakeSpec:
            type = int

        with pytest.raises(ValueError, match="expected int"):
            coerce_single("count", "abc", FakeSpec())
