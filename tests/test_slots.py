"""Tests for named slots: Slot class, validation, gap enforcement, and rendering."""

import pytest
from django.template import Context, Template, TemplateSyntaxError
from django.utils.safestring import SafeString

from dj_design_system.components import BlockComponent
from dj_design_system.parameters import StrParam
from dj_design_system.slots import Slot, validate_slots


# ---------------------------------------------------------------------------
# Test components (defined at module level for template tag registration)
# ---------------------------------------------------------------------------


class SimpleSlottedComponent(BlockComponent):
    """A minimal slotted component for testing."""

    class Meta:
        slots = {
            "body": Slot(required=True, description="Main content"),
            "sidebar": Slot(required=False, description="Optional sidebar"),
        }

    def render(self) -> str:
        sidebar = f"<aside>{self.slots['sidebar']}</aside>" if self.slots.get("sidebar") else ""
        return f"<div class='slotted {self.get_classes_string()}'><main>{self.slots['body']}</main>{sidebar}</div>"


class AllOptionalSlotted(BlockComponent):
    """A slotted component where all slots are optional."""

    class Meta:
        slots = {
            "header": Slot(required=False, default="<h1>Default Header</h1>"),
            "footer": Slot(required=False, default="<footer>Default</footer>"),
        }

    def render(self) -> str:
        return f"<div>{self.slots['header']}{self.slots['footer']}</div>"


class SlottedWithParams(BlockComponent):
    """A slotted component that also has regular params."""

    title = StrParam("A title", required=False)

    class Meta:
        slots = {
            "content": Slot(required=True, description="Main content"),
        }
        positional_args = ["title"]

    def render(self) -> str:
        title_html = f"<h2>{self.title}</h2>" if self.title else ""
        return f"<section>{title_html}{self.slots['content']}</section>"


# ---------------------------------------------------------------------------
# Slot class tests
# ---------------------------------------------------------------------------


class TestSlotClass:
    def test_default_values(self):
        slot = Slot()
        assert slot.required is False
        assert slot.default == ""
        assert slot.description == ""

    def test_custom_values(self):
        slot = Slot(required=True, default="fallback", description="A slot")
        assert slot.required is True
        assert slot.default == "fallback"
        assert slot.description == "A slot"

    def test_repr(self):
        slot = Slot(required=True, description="test")
        assert "required=True" in repr(slot)
        assert "description='test'" in repr(slot)


# ---------------------------------------------------------------------------
# validate_slots tests
# ---------------------------------------------------------------------------


class TestValidateSlots:
    def setup_method(self):
        self.declared = {
            "body": Slot(required=True),
            "sidebar": Slot(required=False, default="<aside></aside>"),
        }

    def test_all_slots_provided(self):
        result = validate_slots(
            self.declared, {"body": "<p>hi</p>", "sidebar": "<nav/>"}, "test"
        )
        assert result == {"body": "<p>hi</p>", "sidebar": "<nav/>"}

    def test_optional_slot_uses_default(self):
        result = validate_slots(self.declared, {"body": "<p>hi</p>"}, "test")
        assert result == {"body": "<p>hi</p>", "sidebar": "<aside></aside>"}

    def test_missing_required_raises(self):
        with pytest.raises(TemplateSyntaxError, match="requires slot 'body'"):
            validate_slots(self.declared, {"sidebar": "x"}, "test")

    def test_unknown_slot_raises(self):
        with pytest.raises(TemplateSyntaxError, match="unknown slot.*nope"):
            validate_slots(self.declared, {"body": "x", "nope": "y"}, "test")

    def test_empty_provided_missing_required(self):
        with pytest.raises(TemplateSyntaxError, match="requires slot 'body'"):
            validate_slots(self.declared, {}, "test")

    def test_all_optional_no_slots_provided(self):
        declared = {
            "header": Slot(required=False, default="H"),
            "footer": Slot(required=False, default="F"),
        }
        result = validate_slots(declared, {}, "test")
        assert result == {"header": "H", "footer": "F"}


# ---------------------------------------------------------------------------
# BlockComponent.has_slots / get_slots tests
# ---------------------------------------------------------------------------


class TestHasSlotsGetSlots:
    def test_slotted_component_has_slots(self):
        assert SimpleSlottedComponent.has_slots() is True

    def test_non_slotted_block_component_has_no_slots(self):
        class PlainBlock(BlockComponent):
            template_format_str = "<div>{content}</div>"

            class Meta:
                pass

        assert PlainBlock.has_slots() is False

    def test_get_slots_returns_declared(self):
        slots = SimpleSlottedComponent.get_slots()
        assert "body" in slots
        assert "sidebar" in slots
        assert slots["body"].required is True
        assert slots["sidebar"].required is False

    def test_get_slots_empty_for_non_slotted(self):
        class PlainBlock(BlockComponent):
            template_format_str = "<div>{content}</div>"

            class Meta:
                pass

        assert PlainBlock.get_slots() == {}


# ---------------------------------------------------------------------------
# Direct instantiation tests
# ---------------------------------------------------------------------------


class TestSlottedComponentInstantiation:
    def test_instantiate_with_all_slots(self):
        comp = SimpleSlottedComponent(
            slots={"body": SafeString("<p>Body</p>"), "sidebar": SafeString("<nav/>")},
        )
        html = comp.render()
        assert "<p>Body</p>" in html
        assert "<nav/>" in html

    def test_instantiate_with_required_only(self):
        comp = SimpleSlottedComponent(
            slots={"body": SafeString("<p>Body</p>")},
        )
        # sidebar is optional with default=""
        html = comp.render()
        assert "<p>Body</p>" in html
        assert "<aside>" not in html

    def test_instantiate_with_params_and_slots(self):
        comp = SlottedWithParams(
            slots={"content": SafeString("<p>Hi</p>")},
            title="Hello",
        )
        html = comp.render()
        assert "<h2>Hello</h2>" in html
        assert "<p>Hi</p>" in html

    def test_all_optional_uses_defaults(self):
        comp = AllOptionalSlotted(slots={})
        html = comp.render()
        assert "Default Header" in html
        assert "Default" in html


# ---------------------------------------------------------------------------
# Template rendering tests (requires Django template engine)
# ---------------------------------------------------------------------------


def _make_slotted_template_library():
    """Create a template library with test slotted components registered."""
    from django import template as template_module

    from dj_design_system.services.slot_node import do_slot, make_slotted_block_tag

    lib = template_module.Library()

    # Register slotted components
    comp_func = make_slotted_block_tag(SimpleSlottedComponent, "simple_slotted")
    lib.tag("simple_slotted", comp_func)

    comp_func2 = make_slotted_block_tag(AllOptionalSlotted, "all_optional")
    lib.tag("all_optional", comp_func2)

    comp_func3 = make_slotted_block_tag(SlottedWithParams, "slotted_with_params")
    lib.tag("slotted_with_params", comp_func3)

    # Register slot tag
    lib.tag("slot", do_slot)

    return lib


@pytest.fixture(autouse=True)
def _register_test_tags():
    """Register test template tags for the duration of each test."""
    from django.template import engines

    lib = _make_slotted_template_library()
    engine = engines["django"]
    engine.engine.template_libraries["test_slots"] = lib
    yield
    engine.engine.template_libraries.pop("test_slots", None)


class TestSlottedTemplateRendering:
    def test_basic_slotted_render(self):
        t = Template(
            "{% load test_slots %}"
            "{% simple_slotted %}"
            '{% slot "body" %}<p>Hello</p>{% endslot %}'
            "{% endsimple_slotted %}"
        )
        result = t.render(Context())
        assert "<p>Hello</p>" in result
        assert "<main>" in result

    def test_multiple_slots(self):
        t = Template(
            "{% load test_slots %}"
            "{% simple_slotted %}"
            '{% slot "body" %}<p>Body</p>{% endslot %}'
            '{% slot "sidebar" %}<nav>Nav</nav>{% endslot %}'
            "{% endsimple_slotted %}"
        )
        result = t.render(Context())
        assert "<p>Body</p>" in result
        assert "<nav>Nav</nav>" in result

    def test_optional_slot_omitted_uses_default(self):
        t = Template(
            "{% load test_slots %}"
            "{% all_optional %}"
            "{% endall_optional %}"
        )
        result = t.render(Context())
        assert "Default Header" in result
        assert "Default" in result

    def test_slot_with_template_variable(self):
        t = Template(
            "{% load test_slots %}"
            "{% simple_slotted %}"
            '{% slot "body" %}<p>{{ greeting }}</p>{% endslot %}'
            "{% endsimple_slotted %}"
        )
        result = t.render(Context({"greeting": "Hi there"}))
        assert "<p>Hi there</p>" in result

    def test_slot_order_does_not_matter(self):
        t = Template(
            "{% load test_slots %}"
            "{% simple_slotted %}"
            '{% slot "sidebar" %}<nav>First</nav>{% endslot %}'
            '{% slot "body" %}<p>Second</p>{% endslot %}'
            "{% endsimple_slotted %}"
        )
        result = t.render(Context())
        assert "<p>Second</p>" in result
        assert "<nav>First</nav>" in result

    def test_slotted_with_positional_param(self):
        t = Template(
            "{% load test_slots %}"
            '{% slotted_with_params "My Title" %}'
            '{% slot "content" %}<p>Body</p>{% endslot %}'
            "{% endslotted_with_params %}"
        )
        result = t.render(Context())
        assert "<h2>My Title</h2>" in result
        assert "<p>Body</p>" in result

    def test_slotted_with_keyword_param(self):
        t = Template(
            "{% load test_slots %}"
            '{% slotted_with_params title="Keyword" %}'
            '{% slot "content" %}<p>Body</p>{% endslot %}'
            "{% endslotted_with_params %}"
        )
        result = t.render(Context())
        assert "<h2>Keyword</h2>" in result


# ---------------------------------------------------------------------------
# Gap enforcement tests (CRITICAL)
# ---------------------------------------------------------------------------


class TestGapEnforcement:
    def test_whitespace_between_slots_is_ok(self):
        t = Template(
            "{% load test_slots %}"
            "{% simple_slotted %}\n"
            '  {% slot "body" %}<p>Body</p>{% endslot %}\n'
            '  {% slot "sidebar" %}<nav/>{% endslot %}\n'
            "{% endsimple_slotted %}"
        )
        # Should not raise
        result = t.render(Context())
        assert "<p>Body</p>" in result

    def test_text_between_slots_raises(self):
        with pytest.raises(TemplateSyntaxError, match="content outside slots"):
            t = Template(
                "{% load test_slots %}"
                "{% simple_slotted %}"
                '{% slot "body" %}<p>Body</p>{% endslot %}'
                "STRAY TEXT"
                '{% slot "sidebar" %}<nav/>{% endslot %}'
                "{% endsimple_slotted %}"
            )
            t.render(Context())

    def test_html_between_slots_raises(self):
        with pytest.raises(TemplateSyntaxError, match="content outside slots"):
            t = Template(
                "{% load test_slots %}"
                "{% simple_slotted %}"
                '{% slot "body" %}<p>Body</p>{% endslot %}'
                "<div>stray</div>"
                '{% slot "sidebar" %}<nav/>{% endslot %}'
                "{% endsimple_slotted %}"
            )
            t.render(Context())

    def test_content_before_first_slot_whitespace_ok(self):
        t = Template(
            "{% load test_slots %}"
            "{% simple_slotted %}   \n"
            '{% slot "body" %}<p>Body</p>{% endslot %}'
            "{% endsimple_slotted %}"
        )
        result = t.render(Context())
        assert "<p>Body</p>" in result

    def test_content_before_first_slot_nonwhitespace_raises(self):
        with pytest.raises(TemplateSyntaxError, match="content outside slots"):
            t = Template(
                "{% load test_slots %}"
                "{% simple_slotted %}"
                "BAD CONTENT"
                '{% slot "body" %}<p>Body</p>{% endslot %}'
                "{% endsimple_slotted %}"
            )
            t.render(Context())

    def test_content_after_last_slot_whitespace_ok(self):
        t = Template(
            "{% load test_slots %}"
            "{% simple_slotted %}"
            '{% slot "body" %}<p>Body</p>{% endslot %}   \n'
            "{% endsimple_slotted %}"
        )
        result = t.render(Context())
        assert "<p>Body</p>" in result

    def test_content_after_last_slot_nonwhitespace_raises(self):
        with pytest.raises(TemplateSyntaxError, match="content outside slots"):
            t = Template(
                "{% load test_slots %}"
                "{% simple_slotted %}"
                '{% slot "body" %}<p>Body</p>{% endslot %}'
                "TRAILING JUNK"
                "{% endsimple_slotted %}"
            )
            t.render(Context())

    def test_other_template_tag_between_slots_raises(self):
        with pytest.raises(TemplateSyntaxError, match="unexpected content between slots"):
            t = Template(
                "{% load test_slots %}"
                "{% simple_slotted %}"
                '{% slot "body" %}<p>Body</p>{% endslot %}'
                "{% now \"Y\" %}"
                '{% slot "sidebar" %}<nav/>{% endslot %}'
                "{% endsimple_slotted %}"
            )
            t.render(Context())

    def test_django_comment_between_slots_is_ok(self):
        t = Template(
            "{% load test_slots %}"
            "{% simple_slotted %}"
            '{# This is a comment #}'
            '{% slot "body" %}<p>Body</p>{% endslot %}'
            "{% endsimple_slotted %}"
        )
        # Django comments are removed during parsing, so they won't appear
        # as nodes at all — this should just work
        result = t.render(Context())
        assert "<p>Body</p>" in result

    def test_error_message_includes_component_name(self):
        with pytest.raises(TemplateSyntaxError, match="simple_slotted"):
            t = Template(
                "{% load test_slots %}"
                "{% simple_slotted %}"
                "OOPS"
                '{% slot "body" %}<p>Body</p>{% endslot %}'
                "{% endsimple_slotted %}"
            )
            t.render(Context())

    def test_error_message_includes_content_snippet(self):
        with pytest.raises(TemplateSyntaxError, match="OOPS"):
            t = Template(
                "{% load test_slots %}"
                "{% simple_slotted %}"
                "OOPS"
                '{% slot "body" %}<p>Body</p>{% endslot %}'
                "{% endsimple_slotted %}"
            )
            t.render(Context())


# ---------------------------------------------------------------------------
# Slot validation errors in templates
# ---------------------------------------------------------------------------


class TestSlotValidationInTemplates:
    def test_missing_required_slot_raises(self):
        with pytest.raises(TemplateSyntaxError, match="requires slot 'body'"):
            t = Template(
                "{% load test_slots %}"
                "{% simple_slotted %}"
                '{% slot "sidebar" %}<nav/>{% endslot %}'
                "{% endsimple_slotted %}"
            )
            t.render(Context())

    def test_unknown_slot_name_raises(self):
        with pytest.raises(TemplateSyntaxError, match="unknown slot.*nope"):
            t = Template(
                "{% load test_slots %}"
                "{% simple_slotted %}"
                '{% slot "body" %}<p>Body</p>{% endslot %}'
                '{% slot "nope" %}<p>Bad</p>{% endslot %}'
                "{% endsimple_slotted %}"
            )
            t.render(Context())

    def test_duplicate_slot_name_raises(self):
        with pytest.raises(TemplateSyntaxError, match="duplicate slot 'body'"):
            t = Template(
                "{% load test_slots %}"
                "{% simple_slotted %}"
                '{% slot "body" %}<p>First</p>{% endslot %}'
                '{% slot "body" %}<p>Second</p>{% endslot %}'
                "{% endsimple_slotted %}"
            )
            t.render(Context())

    def test_slot_tag_requires_name_argument(self):
        with pytest.raises(TemplateSyntaxError, match="requires exactly one argument"):
            Template(
                "{% load test_slots %}"
                "{% simple_slotted %}"
                "{% slot %}<p>No name</p>{% endslot %}"
                "{% endsimple_slotted %}"
            )


# ---------------------------------------------------------------------------
# Backward compatibility — non-slotted BlockComponent still works
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_non_slotted_block_component_works(self):
        class PlainAlert(BlockComponent):
            template_format_str = "<div class='alert {classes}'>{content}</div>"

            class Meta:
                pass

        comp = PlainAlert(content=SafeString("<p>Warning!</p>"))
        html = comp.render()
        assert "<p>Warning!</p>" in html
        assert "alert" in html

    def test_non_slotted_has_no_slots(self):
        class PlainAlert(BlockComponent):
            template_format_str = "<div>{content}</div>"

            class Meta:
                pass

        assert PlainAlert.has_slots() is False
        assert PlainAlert.get_slots() == {}

    def test_non_slotted_as_tag_returns_callable(self):
        class PlainAlert(BlockComponent):
            template_format_str = "<div>{content}</div>"

            class Meta:
                pass

        tag_func = PlainAlert.as_tag()
        # Should be a simple callable, not a compilation function
        assert callable(tag_func)
        result = tag_func(SafeString("hello"))
        assert "hello" in str(result)


# ---------------------------------------------------------------------------
# Integration tests — SlottedCardComponent via design_components library
# ---------------------------------------------------------------------------


class TestSlottedCardIntegration:
    """Tests using the real registered slotted_card tag via {% load design_components %}."""

    def test_card_with_all_slots(self):
        t = Template(
            "{% load design_components %}"
            '{% slotted_card title="Welcome" %}'
            '{% slot "header" %}<img src="banner.jpg">{% endslot %}'
            '{% slot "body" %}<p>Main content.</p>{% endslot %}'
            '{% slot "footer" %}<button>OK</button>{% endslot %}'
            "{% endslotted_card %}"
        )
        result = t.render(Context())
        assert "slotted-card__header" in result
        assert "<img src" in result
        assert "<p>Main content.</p>" in result
        assert "slotted-card__footer" in result
        assert "<button>OK</button>" in result
        assert "slotted-card__title" in result
        assert "Welcome" in result

    def test_card_with_only_required_slot(self):
        t = Template(
            "{% load design_components %}"
            "{% slotted_card %}"
            '{% slot "body" %}<p>Just body.</p>{% endslot %}'
            "{% endslotted_card %}"
        )
        result = t.render(Context())
        assert "<p>Just body.</p>" in result
        assert "slotted-card__header" not in result
        assert "slotted-card__footer" not in result
        assert "slotted-card__title" not in result

    def test_card_with_variant(self):
        t = Template(
            "{% load design_components %}"
            '{% slotted_card variant="elevated" %}'
            '{% slot "body" %}<p>Content.</p>{% endslot %}'
            "{% endslotted_card %}"
        )
        result = t.render(Context())
        assert "elevated" in result

    def test_card_with_positional_title(self):
        t = Template(
            "{% load design_components %}"
            '{% slotted_card "My Title" %}'
            '{% slot "body" %}<p>Content.</p>{% endslot %}'
            "{% endslotted_card %}"
        )
        result = t.render(Context())
        assert "My Title" in result

    def test_card_slot_with_template_variable(self):
        t = Template(
            "{% load design_components %}"
            "{% slotted_card %}"
            '{% slot "body" %}<p>{{ message }}</p>{% endslot %}'
            "{% endslotted_card %}"
        )
        result = t.render(Context({"message": "Dynamic!"}))
        assert "<p>Dynamic!</p>" in result

    def test_card_nested_inside_another_component(self):
        t = Template(
            "{% load design_components %}"
            '{% alert "info" %}'
            '{% slotted_card title="Nested" %}'
            '{% slot "body" %}<p>Inside alert.</p>{% endslot %}'
            "{% endslotted_card %}"
            "{% endalert %}"
        )
        result = t.render(Context())
        assert "alert" in result
        assert "slotted-card" in result
        assert "<p>Inside alert.</p>" in result

    def test_card_slot_containing_other_component(self):
        t = Template(
            "{% load design_components %}"
            "{% slotted_card %}"
            '{% slot "body" %}{% badge "New" %}{% endslot %}'
            "{% endslotted_card %}"
        )
        result = t.render(Context())
        assert "badge" in result
        assert "New" in result

    def test_card_missing_required_body_raises(self):
        with pytest.raises(TemplateSyntaxError, match="requires slot 'body'"):
            t = Template(
                "{% load design_components %}"
                "{% slotted_card %}"
                '{% slot "header" %}<h1>No body</h1>{% endslot %}'
                "{% endslotted_card %}"
            )
            t.render(Context())

    def test_card_gap_content_raises(self):
        with pytest.raises(TemplateSyntaxError, match="content outside slots"):
            t = Template(
                "{% load design_components %}"
                "{% slotted_card %}"
                "STRAY CONTENT"
                '{% slot "body" %}<p>Body</p>{% endslot %}'
                "{% endslotted_card %}"
            )
            t.render(Context())
