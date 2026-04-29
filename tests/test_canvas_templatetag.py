"""Tests for the canvas template tag."""

import pytest
from django.template import Context, Template

pytestmark = pytest.mark.django_db


class TestCanvasTemplateTag:
    """Test the {% canvas %}...{% endcanvas %} block tag."""

    def test_renders_iframe_element(self):
        """The canvas tag should output an <iframe> element."""
        template = Template(
            "{% load dj_design_system_gallery %}"
            "{% canvas %}<p>Hello</p>{% endcanvas %}"
        )
        result = template.render(Context())
        assert "<iframe" in result
        assert "srcdoc=" in result
        assert 'class="gallery-canvas"' in result

    def test_inner_content_appears_in_srcdoc(self):
        """The rendered inner content should appear inside the srcdoc attribute."""
        template = Template(
            "{% load dj_design_system_gallery %}"
            "{% canvas %}<p>Test content</p>{% endcanvas %}"
        )
        result = template.render(Context())
        # Content is HTML-escaped inside srcdoc attribute
        assert "Test content" in result

    def test_srcdoc_contains_html_document(self):
        """The srcdoc should contain a full HTML document structure."""
        template = Template(
            "{% load dj_design_system_gallery %}"
            "{% canvas %}<span>X</span>{% endcanvas %}"
        )
        result = template.render(Context())
        # The srcdoc value is HTML-escaped, so check for escaped versions
        assert "&lt;!DOCTYPE html&gt;" in result or "DOCTYPE" in result

    def test_canvas_wrapper_has_background_class(self):
        """The canvas wrapper inside srcdoc should have a background class."""
        template = Template(
            "{% load dj_design_system_gallery %}"
            "{% canvas %}<span>X</span>{% endcanvas %}"
        )
        result = template.render(Context())
        assert "canvas-bg-" in result

    def test_no_sandbox_attribute(self):
        """The iframe should not have a sandbox attribute (trusted components)."""
        template = Template(
            "{% load dj_design_system_gallery %}"
            "{% canvas %}<span>X</span>{% endcanvas %}"
        )
        result = template.render(Context())
        assert "sandbox" not in result

    def test_canvas_css_included(self):
        """The canvas.css stylesheet should be referenced in the srcdoc."""
        template = Template(
            "{% load dj_design_system_gallery %}"
            "{% canvas %}<span>X</span>{% endcanvas %}"
        )
        result = template.render(Context())
        assert "canvas.css" in result
