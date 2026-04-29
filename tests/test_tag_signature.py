"""Tests for tag_signature module that generates template tag usage examples."""

from dj_design_system.components import BlockComponent, TagComponent
from dj_design_system.data import BLOCK_CONTENT_PLACEHOLDER
from dj_design_system.parameters import (
    BoolCSSClassParam,
    BoolParam,
    StrCSSClassParam,
    StrParam,
)
from dj_design_system.parameters.base import BaseParam
from dj_design_system.services.tag_signature import (
    generate_current_tag_signature,
    generate_tag_signature,
)


class SimpleTagComponent(TagComponent):
    """A simple tag component with one required string parameter."""

    name = StrParam("The name parameter")

    class Meta:
        positional_args = ["name"]

    template_format_str = "<div>{name}</div>"


class TagComponentWithOptional(TagComponent):
    """A tag component with required and optional parameters."""

    label = StrParam("The label")
    size = StrCSSClassParam("Size option", required=False, choices=["small", "large"])
    dark = BoolCSSClassParam(required=False, default=False)

    class Meta:
        positional_args = ["label"]

    template_format_str = "<button class='{classes}'>{label}</button>"


class TagComponentMultiplePositional(TagComponent):
    """A tag component with multiple positional arguments."""

    url = StrParam("The URL")
    label = StrParam("The link label")

    class Meta:
        positional_args = ["url", "label"]

    template_format_str = "<a href='{url}'>{label}</a>"


# ---------------------------------------------------------------------------
# Additional component helpers for gap coverage
# ---------------------------------------------------------------------------


class IntParam(BaseParam):
    """Custom integer parameter for testing non-standard type fallback."""

    type = int


class BoolPositionalComponent(TagComponent):
    """Component with a boolean default positional arg."""

    enabled = BoolParam(required=False, default=True)

    class Meta:
        positional_args = ["enabled"]

    template_format_str = "<div>{enabled}</div>"


class IntKwargComponent(TagComponent):
    """Component with a custom int keyword arg (non-str, non-bool)."""

    count = IntParam("A count", required=False, default=42)

    template_format_str = "<div>{count}</div>"


class IntPositionalComponent(TagComponent):
    """Component with a custom int positional arg."""

    count = IntParam("A count", default=42)

    class Meta:
        positional_args = ["count"]

    template_format_str = "<div>{count}</div>"


class BlockNoParamsComponent(BlockComponent):
    """Block component with no parameters at all."""

    template_format_str = "<div>{content}</div>"


class BlockMultiKwargComponent(BlockComponent):
    """Block component with multiple optional keyword parameters."""

    heading = StrParam("The heading", required=False)
    level = StrCSSClassParam("Level", required=False, choices=["info", "warning"])

    template_format_str = "<div class='{level}'><h3>{heading}</h3>{content}</div>"


class RequiredKwargComponent(TagComponent):
    """Component with a required non-positional keyword param."""

    label = StrParam("The label")

    template_format_str = "<button>{label}</button>"


class BoolCSSNoDefaultComponent(TagComponent):
    """Component with BoolCSSClassParam that has no default."""

    text = StrParam("Text")
    active = BoolCSSClassParam(required=False)  # no default

    class Meta:
        positional_args = ["text"]

    template_format_str = "<span class='{classes}'>{text}</span>"


class CustomNullValueComponent(TagComponent):
    """Component with a custom param type that generates None as example value."""

    count = IntParam("A count", required=False)  # no default, no choices

    template_format_str = "<div>{count}</div>"


class GhostPositionalComponent(TagComponent):
    """Component with positional_args listing a name not in params."""

    template_format_str = "<div></div>"

    class Meta:
        positional_args = ["nonexistent"]


class SimpleBlockComponent(BlockComponent):
    """A simple block component with no positional args."""

    heading = StrParam("Heading", required=False)

    template_format_str = "<div><h3>{heading}</h3>{content}</div>"


class BlockComponentWithPositional(BlockComponent):
    """A block component with positional args."""

    level = StrCSSClassParam(
        "Alert level", default="info", choices=["info", "warning", "error"]
    )

    class Meta:
        positional_args = ["level"]

    template_format_str = "<div class='alert-{level}'>{content}</div>"


class TestGenerateTagSignature:
    """Test suite for generate_tag_signature function."""

    def test_simple_tag_component_minimal(self):
        """Test minimal usage for a simple tag component."""
        sig = generate_tag_signature(SimpleTagComponent)
        assert sig.minimal == '{% simple_tag "foo" %}'

    def test_simple_tag_component_maximal(self):
        """Test maximal usage for a simple tag component."""
        sig = generate_tag_signature(SimpleTagComponent)
        assert sig.maximal == '{% simple_tag "foo" %}'

    def test_tag_with_optional_params_minimal(self):
        """Test minimal usage shows only required positional args."""
        sig = generate_tag_signature(TagComponentWithOptional)
        assert sig.minimal == '{% tag_component_with_optional "foo" %}'

    def test_tag_with_optional_params_maximal(self):
        """Test maximal usage includes optional parameters."""
        sig = generate_tag_signature(TagComponentWithOptional)
        # size should use first choice "small", dark should use default False
        assert "{% tag_component_with_optional" in sig.maximal
        assert '"foo"' in sig.maximal  # positional arg
        assert 'size="small"' in sig.maximal
        assert "dark=False" in sig.maximal

    def test_component_with_multiple_positional_args_minimal(self):
        """Test minimal for component with multiple required positional args."""
        sig = generate_tag_signature(TagComponentMultiplePositional)
        assert sig.minimal == '{% tag_component_multiple_positional "foo" "bar" %}'

    def test_component_with_multiple_positional_args_maximal(self):
        """Test maximal for component with multiple positional args."""
        sig = generate_tag_signature(TagComponentMultiplePositional)
        # Both are positional, so maximal should match minimal
        assert sig.maximal == '{% tag_component_multiple_positional "foo" "bar" %}'

    def test_simple_block_component_minimal(self):
        """Test minimal usage for a block component without positional args."""
        sig = generate_tag_signature(SimpleBlockComponent)
        assert (
            sig.minimal
            == f"{{% simple_block %}}{BLOCK_CONTENT_PLACEHOLDER}{{% endsimple_block %}}"
        )

    def test_simple_block_component_maximal(self):
        """Test maximal usage for a block component."""
        sig = generate_tag_signature(SimpleBlockComponent)
        # heading is optional, so maximal should show it
        assert "{% simple_block" in sig.maximal
        assert 'heading="foo"' in sig.maximal
        assert BLOCK_CONTENT_PLACEHOLDER in sig.maximal
        assert "{% endsimple_block %}" in sig.maximal

    def test_block_with_positional_args_minimal(self):
        """Test minimal for block component with positional args."""
        sig = generate_tag_signature(BlockComponentWithPositional)
        # level has default, so minimal might not include it (check required attribute)
        # Actually, level has choices and default, so it uses the default
        assert "info" in sig.minimal

    def test_block_with_positional_args_maximal(self):
        """Test maximal for block component with positional args."""
        sig = generate_tag_signature(BlockComponentWithPositional)
        # level has choices, should use first choice "info"
        assert "level=" in sig.maximal or "info" in sig.maximal

    def test_string_example_cycling(self):
        """Test that string examples cycle through foo, bar, baz."""

        class ThreeStringParams(TagComponent):
            """Component with three string parameters."""

            p1 = StrParam("First")
            p2 = StrParam("Second", required=False)
            p3 = StrParam("Third", required=False)

            class Meta:
                positional_args = ["p1"]

            template_format_str = "<div>{p1} {p2} {p3}</div>"

        sig = generate_tag_signature(ThreeStringParams)
        # p1 is positional so it's just the value; p2 and p3 are keyword args
        assert '"foo"' in sig.maximal  # p1 is positional, not named
        assert 'p2="bar"' in sig.maximal
        assert 'p3="baz"' in sig.maximal

    def test_usage_description_present(self):
        """Test that TagSignature has all required fields."""
        sig = generate_tag_signature(SimpleTagComponent)
        assert hasattr(sig, "minimal")
        assert hasattr(sig, "maximal")
        assert hasattr(sig, "minimal_html")
        assert hasattr(sig, "maximal_html")
        assert isinstance(sig.minimal, str)
        assert isinstance(sig.maximal, str)
        assert isinstance(sig.minimal_html, str)
        assert isinstance(sig.maximal_html, str)


class TestGenerateCurrentTagSignature:
    """Test suite for generate_current_tag_signature function."""

    def test_block_component_uses_content_value_when_present(self):
        """Current signature should render explicit block content from kwargs."""
        sig = generate_current_tag_signature(
            SimpleBlockComponent,
            {"heading": "Hello", "content": "Custom body"},
        )

        assert "Custom body" in sig.minimal
        assert "content=" not in sig.minimal
        assert "{% endsimple_block %}" in sig.minimal

    def test_block_component_uses_placeholder_when_content_missing(self):
        """Current signature should fall back to BLOCK_CONTENT_PLACEHOLDER."""
        sig = generate_current_tag_signature(SimpleBlockComponent, {})

        assert BLOCK_CONTENT_PLACEHOLDER in sig.minimal
        assert "...content..." not in sig.minimal

    def test_tag_component_current_signature(self):
        """generate_current_tag_signature works for non-block components."""
        sig = generate_current_tag_signature(SimpleTagComponent, {"name": "hello"})
        assert '{% simple_tag "hello" %}' == sig.minimal

    def test_tag_component_current_no_args(self):
        """Non-block component with empty kwargs renders just the tag."""
        sig = generate_current_tag_signature(SimpleTagComponent, {})
        assert "{% simple_tag %}" == sig.minimal


# ---------------------------------------------------------------------------
# Additional coverage: format helpers and edge-case generate_tag_signature
# ---------------------------------------------------------------------------


class TestTagSignatureEdgeCases:
    def test_bool_positional_arg(self):
        """BoolParam positional arg → _format_positional_arg bool branch."""
        sig = generate_tag_signature(BoolPositionalComponent)
        # The minimal has no required bool positional, but maximal has default=True
        assert "True" in sig.maximal

    def test_int_keyword_arg(self):
        """IntParam with default → _format_param_for_tag non-str/bool fallback."""
        sig = generate_tag_signature(IntKwargComponent)
        assert "count=42" in sig.maximal

    def test_int_positional_arg(self):
        """IntParam positional → _format_positional_arg non-str/bool fallback."""
        sig = generate_tag_signature(IntPositionalComponent)
        assert "42" in sig.minimal

    def test_block_no_params_empty_args_str(self):
        """Block component with no params → maximal has no arg string."""
        sig = generate_tag_signature(BlockNoParamsComponent)
        assert "{% block_no_params %}" in sig.minimal

    def test_block_multi_kwarg_multiline(self):
        """Block component with 2+ keyword params → multiline format."""
        sig = generate_tag_signature(BlockMultiKwargComponent)
        assert "{% block_multi_kwarg" in sig.maximal
        assert "heading" in sig.maximal
        assert "level" in sig.maximal

    def test_required_kwarg_skipped_in_maximal(self):
        """Required non-positional params are omitted from the maximal signature."""
        sig = generate_tag_signature(RequiredKwargComponent)
        # label is required but not positional → not in positional_args → skipped
        assert "{% required_kwarg %}" == sig.maximal

    def test_bool_css_no_default_generates_true(self):
        """BoolCSSClassParam with no default returns True as example value."""
        sig = generate_tag_signature(BoolCSSNoDefaultComponent)
        assert "active=True" in sig.maximal

    def test_custom_null_value_param_skipped(self):
        """Custom param type that returns None is skipped in maximal signature."""
        sig = generate_tag_signature(CustomNullValueComponent)
        assert "count" not in sig.maximal

    def test_ghost_positional_skipped(self):
        """Positional arg not in params is gracefully skipped."""
        sig = generate_tag_signature(GhostPositionalComponent)
        assert "nonexistent" not in sig.minimal
