"""Tests for the markdown canvas preprocessor and extension."""

import pytest
from django.test import override_settings
from django.urls import reverse

from dj_design_system.services.markdown_canvas import (
    CanvasExtension,
    CanvasPreprocessor,
    DjangoLangPreprocessor,
    parse_tag_syntax,
)


# ---------------------------------------------------------------------------
# parse_tag_syntax
# ---------------------------------------------------------------------------


class TestParseTagSyntax:
    """Test the Django template tag syntax parser."""

    def test_simple_tag(self):
        spec = parse_tag_syntax('{% icon "check" %}')
        assert spec.component_name == "icon"
        assert spec.positional_args == ("check",)
        assert spec.params == {}

    def test_tag_with_kwargs(self):
        spec = parse_tag_syntax('{% icon "check" size="large" %}')
        assert spec.component_name == "icon"
        assert spec.positional_args == ("check",)
        assert spec.params == {"size": "large"}

    def test_tag_with_only_kwargs(self):
        spec = parse_tag_syntax('{% button label="Click me" %}')
        assert spec.component_name == "button"
        assert spec.positional_args == ()
        assert spec.params == {"label": "Click me"}

    def test_tag_with_multiple_positional_args(self):
        spec = parse_tag_syntax('{% tag "foo" "bar" %}')
        assert spec.component_name == "tag"
        assert spec.positional_args == ("foo", "bar")

    def test_tag_with_multiple_kwargs(self):
        spec = parse_tag_syntax('{% icon name="check" size="large" color="red" %}')
        assert spec.component_name == "icon"
        assert spec.params == {"name": "check", "size": "large", "color": "red"}

    def test_tag_with_unquoted_kwargs(self):
        spec = parse_tag_syntax("{% icon name=check size=large %}")
        assert spec.component_name == "icon"
        assert spec.params == {"name": "check", "size": "large"}

    def test_tag_with_unquoted_boolean_kwarg(self):
        spec = parse_tag_syntax("{% callout highlight=True %}Warning{% endcallout %}")
        assert spec.component_name == "callout"
        assert spec.params == {"highlight": "True", "content": "Warning"}

    def test_block_tag_with_content(self):
        spec = parse_tag_syntax(
            '{% callout type="warning" %}This is a warning{% endcallout %}'
        )
        assert spec.component_name == "callout"
        assert spec.params == {"type": "warning", "content": "This is a warning"}

    def test_block_tag_no_kwargs(self):
        spec = parse_tag_syntax("{% panel %}Some content{% endpanel %}")
        assert spec.component_name == "panel"
        assert spec.params == {"content": "Some content"}

    def test_empty_source_raises(self):
        with pytest.raises(ValueError, match="Empty canvas block"):
            parse_tag_syntax("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="Empty canvas block"):
            parse_tag_syntax("   ")

    def test_invalid_syntax_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_tag_syntax("not a template tag")

    def test_single_quoted_args(self):
        spec = parse_tag_syntax("{% icon 'check' size='large' %}")
        assert spec.positional_args == ("check",)
        assert spec.params == {"size": "large"}

    def test_tag_with_no_args(self):
        spec = parse_tag_syntax("{% spacer %}")
        assert spec.component_name == "spacer"
        assert spec.positional_args == ()
        assert spec.params == {}


# ---------------------------------------------------------------------------
# CanvasPreprocessor
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.django_db


class TestCanvasPreprocessor:
    """Test the preprocessor that replaces fenced canvas blocks."""

    def _process(self, text, debug=False):
        """Run the preprocessor on markdown text, return joined output."""
        import markdown

        md = markdown.Markdown()
        canvas_base_url = reverse("gallery-canvas-iframe")
        preprocessor = CanvasPreprocessor(md, canvas_base_url, debug=debug)
        lines = text.split("\n")
        result = preprocessor.run(lines)
        return "\n".join(result)

    def test_simple_canvas_block(self):
        text = '```canvas\n{% button "Click" %}\n```'
        result = self._process(text)
        assert "gallery-md-canvas" in result
        assert "gallery-md-canvas__iframe" in result
        assert "gallery-md-canvas__code" in result
        assert "component=button" in result

    def test_iframe_has_lazy_loading(self):
        """Iframes should defer loading until near the viewport for performance."""
        text = '```canvas\n{% button "Click" %}\n```'
        result = self._process(text)
        assert 'loading="lazy"' in result

    def test_canvas_block_with_kwargs(self):
        text = '```canvas\n{% button label="Hello" %}\n```'
        result = self._process(text)
        assert "component=button" in result
        assert "label=Hello" in result

    def test_block_component_canvas(self):
        text = '```canvas\n{% alert "warning" %}Danger!{% endalert %}\n```'
        result = self._process(text)
        assert "component=alert" in result
        assert "gallery-md-canvas" in result

    def test_basic_mode_appended(self):
        text = '```canvas\n{% button "Click" %}\n```'
        result = self._process(text)
        assert "mode=basic" in result

    def test_multiple_canvas_blocks(self):
        text = (
            '```canvas\n{% button "One" %}\n```\n\n'
            "Some text between.\n\n"
            '```canvas\n{% button "Two" %}\n```'
        )
        result = self._process(text)
        assert result.count("gallery-md-canvas") >= 2

    def test_toggle_radios_present(self):
        text = '```canvas\n{% button "Click" %}\n```'
        result = self._process(text)
        assert "mc-toggle-" in result
        assert 'gallery-md-canvas__input--both"' in result
        assert 'gallery-md-canvas__input--preview"' in result
        assert 'gallery-md-canvas__input--code"' in result

    def test_invalid_syntax_shows_error(self):
        text = "```canvas\nnot a template tag\n```"
        result = self._process(text)
        assert "Canvas error" in result
        assert "Cannot parse" in result

    def test_invalid_syntax_debug_shows_source(self):
        text = "```canvas\nnot a template tag\n```"
        result = self._process(text, debug=True)
        assert "Canvas error" in result
        assert "not a template tag" in result

    def test_invalid_syntax_no_debug_hides_source(self):
        text = "```canvas\nnot a template tag\n```"
        result = self._process(text, debug=False)
        assert "Canvas error" in result
        # Source should NOT appear in a <pre><code> after the error
        assert "<pre><code>" not in result

    def test_non_canvas_fenced_blocks_preserved(self):
        text = "```python\ndef hello():\n    pass\n```"
        result = self._process(text)
        # Should be untouched by the canvas preprocessor
        assert "gallery-md-canvas" not in result
        assert "def hello():" in result

    def test_highlighted_code_in_widget(self):
        text = '```canvas\n{% button "Click" %}\n```'
        result = self._process(text)
        assert "gallery-usage__code" in result

    def test_unique_ids_per_block(self):
        text = '```canvas\n{% button "A" %}\n```\n\n```canvas\n{% button "B" %}\n```'
        result = self._process(text)
        assert "mc-toggle-1" in result
        assert "mc-toggle-2" in result


# ---------------------------------------------------------------------------
# CanvasExtension integration
# ---------------------------------------------------------------------------


class TestCanvasExtension:
    """Test the full markdown extension wired into the markdown pipeline."""

    def _render(self, text, debug=False):
        import markdown

        canvas_base_url = reverse("gallery-canvas-iframe")
        md = markdown.Markdown(
            extensions=[
                CanvasExtension(canvas_base_url=canvas_base_url, debug=debug),
                "fenced_code",
                "tables",
                "toc",
            ]
        )
        return md.convert(text)

    def test_canvas_block_rendered_in_full_pipeline(self):
        text = '```canvas\n{% button "Click" %}\n```'
        html = self._render(text)
        assert "gallery-md-canvas" in html

    def test_regular_fenced_code_still_works(self):
        text = "```python\nprint('hello')\n```"
        html = self._render(text)
        assert "<code" in html
        assert "gallery-md-canvas" not in html

    def test_mixed_content(self):
        text = (
            "# Heading\n\n"
            "Some text.\n\n"
            '```canvas\n{% button "Click" %}\n```\n\n'
            "```python\nx = 1\n```"
        )
        html = self._render(text)
        assert "gallery-md-canvas" in html
        assert "<h1" in html
        assert "x = 1" in html

    def test_adjacent_canvas_blocks_do_not_leak_into_code_fences(self):
        text = (
            '```canvas\n{% icon "arrow-blue-bg" %}\n```\n\n'
            '```canvas\n{% icon "arrow-left" %}\n```'
        )
        html = self._render(text)
        assert html.count("gallery-md-canvas") >= 2
        assert "```canvas" not in html
        assert "```html+django" not in html


# ---------------------------------------------------------------------------
# Codehilite integration
# ---------------------------------------------------------------------------


class TestCodehilite:
    """Test that codehilite produces Pygments-highlighted fenced blocks."""

    def test_codehilite_produces_highlighted_output(self):
        import markdown

        md = markdown.Markdown(
            extensions=["fenced_code", "codehilite"],
            extension_configs={
                "codehilite": {
                    "css_class": "gallery-highlight",
                    "noclasses": False,
                    "pygments_style": "monokai",
                }
            },
        )
        result = md.convert("```python\ndef hello():\n    pass\n```")
        assert "gallery-highlight" in result
        assert "<span" in result

    def test_django_template_syntax_highlighted(self):
        import markdown

        md = markdown.Markdown(
            extensions=["fenced_code", "codehilite"],
            extension_configs={
                "codehilite": {
                    "css_class": "gallery-highlight",
                    "noclasses": False,
                    "pygments_style": "monokai",
                }
            },
        )
        result = md.convert('```html+django\n{% icon "check" %}\n```')
        assert "gallery-highlight" in result
        assert "<span" in result

    @override_settings(dj_design_system={"GALLERY_CODEHILITE_STYLE": ""})
    def test_codehilite_disabled_when_style_empty(self):
        from dj_design_system.settings import dds_settings

        assert dds_settings.GALLERY_CODEHILITE_STYLE == ""


# ---------------------------------------------------------------------------
# DjangoLangPreprocessor
# ---------------------------------------------------------------------------


class TestDjangoLangPreprocessor:
    """Test auto-retagging of fenced blocks containing Django syntax."""

    def _process(self, text):
        import markdown

        md = markdown.Markdown()
        preprocessor = DjangoLangPreprocessor(md)
        return "\n".join(preprocessor.run(text.split("\n")))

    def test_no_lang_with_django_syntax_retagged(self):
        text = '```\n{% icon "check" %}\n```'
        result = self._process(text)
        assert "```html+django" in result

    def test_py_with_django_syntax_retagged(self):
        text = '```py\n{% icon "check" %}\n```'
        result = self._process(text)
        assert "```html+django" in result

    def test_python_with_django_syntax_retagged(self):
        text = '```python\n{% icon "check" %}\n```'
        result = self._process(text)
        assert "```html+django" in result

    def test_py_without_django_syntax_unchanged(self):
        text = "```py\nx = 1\n```"
        result = self._process(text)
        assert "```py" in result
        assert "html+django" not in result

    def test_no_lang_without_django_syntax_unchanged(self):
        text = "```\nhello world\n```"
        result = self._process(text)
        assert "html+django" not in result

    def test_explicit_language_not_retagged(self):
        text = '```javascript\n{% icon "check" %}\n```'
        result = self._process(text)
        assert "```javascript" in result
        assert "html+django" not in result

    def test_double_brace_syntax_detected(self):
        text = "```\n{{ variable }}\n```"
        result = self._process(text)
        assert "```html+django" in result
