from django.utils.html import format_html

from dj_design_system.components import BaseComponent, BlockComponent
from dj_design_system.parameters import StrParam


class StubComponent(BaseComponent):
    """A minimal component for testing."""

    label = StrParam("A text label.", default="hello")
    template_format_str = "<span class='{classes}'>{label}</span>"


class StubBlockComponent(BlockComponent):
    """A minimal block component for testing."""

    template_format_str = "<div class='{classes}'>{content}</div>"


class TestBaseComponentRendering:
    """Tests for __str__ and __html__ on BaseComponent."""

    def test_str_returns_rendered_html(self):
        """str() on a component returns the rendered HTML."""
        result = str(StubComponent(label="world"))
        assert "<span" in result
        assert "world" in result

    def test_html_returns_rendered_html(self):
        """__html__() returns the same output as render()."""
        component = StubComponent(label="world")
        assert component.__html__() == component.render()

    def test_str_matches_render(self):
        """str() and render() produce identical output."""
        component = StubComponent(label="test")
        assert str(component) == component.render()

    def test_format_html_does_not_double_escape(self):
        """A component passed to format_html is not double-escaped."""
        component = StubComponent(label="test")
        result = format_html("<div>{}</div>", component)
        # The inner <span> should be preserved, not escaped to &lt;span&gt;
        assert "<span" in result
        assert "&lt;span" not in result


class TestBlockComponentRendering:
    """Tests for __str__ and __html__ on BlockComponent."""

    def test_str_returns_rendered_html(self):
        """str() on a block component returns the rendered HTML with content."""
        result = str(StubBlockComponent(content="inner text"))
        assert "<div" in result
        assert "inner text" in result

    def test_html_returns_rendered_html(self):
        """__html__() returns the same output as render()."""
        component = StubBlockComponent(content="inner text")
        assert component.__html__() == component.render()

    def test_format_html_does_not_double_escape(self):
        """A block component passed to format_html is not double-escaped."""
        component = StubBlockComponent(content="inner")
        result = format_html("<section>{}</section>", component)
        assert "<div" in result
        assert "&lt;div" not in result


class TestNestedComponentRendering:
    """Tests for components nested inside other components via format_html."""

    def test_component_in_format_html_kwarg(self):
        """A component used as a format_html keyword argument renders correctly."""
        inner = StubComponent(label="nested")
        result = format_html("<div>{inner}</div>", inner=inner)
        assert "<span" in result
        assert "nested" in result
        assert "&lt;span" not in result
