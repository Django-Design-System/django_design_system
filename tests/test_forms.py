"""Tests for the component parameter form factory."""

import pytest
from django import forms

from dj_design_system.components import TagComponent
from dj_design_system.forms import build_component_form
from dj_design_system.parameters import (
    BoolCSSClassParam,
    BoolParam,
    StrCSSClassParam,
    StrParam,
)
from example_project.demo_components.components.user_card import UserCardComponent


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Minimal test components — defined inline to keep tests self-contained
# ---------------------------------------------------------------------------


class _StrParamComponent(TagComponent):
    """A component with an optional plain StrParam."""

    template_format_str = "<div>{text}</div>"
    text = StrParam("Some text.", required=False)


class _RequiredStrParamComponent(TagComponent):
    """A component with a required plain StrParam."""

    template_format_str = "<div>{text}</div>"
    text = StrParam("Some text.", required=True)


class _StrParamWithChoicesComponent(TagComponent):
    """A component with an optional StrParam restricted to choices."""

    template_format_str = "<div class='{classes}'></div>"
    size = StrParam("Size variant.", required=False, choices=["sm", "md", "lg"])


class _RequiredStrParamWithChoicesComponent(TagComponent):
    """A component with a required StrParam restricted to choices."""

    template_format_str = "<div class='{classes}'></div>"
    size = StrParam("Size variant.", required=True, choices=["sm", "md", "lg"])


class _BoolParamComponent(TagComponent):
    """A component with a BoolParam."""

    template_format_str = "<div class='{classes}'></div>"
    active = BoolParam("Whether active.", required=False)


class _BoolCSSClassParamComponent(TagComponent):
    """A component with a BoolCSSClassParam."""

    template_format_str = "<div class='{classes}'></div>"
    active = BoolCSSClassParam("Whether active.", required=False)


class _StrCSSClassParamComponent(TagComponent):
    """A component with a StrCSSClassParam (always has choices)."""

    template_format_str = "<div class='{classes}'></div>"
    size = StrCSSClassParam("Size variant.", required=False, choices=["sm", "md", "lg"])


# ---------------------------------------------------------------------------
# Field type mapping
# ---------------------------------------------------------------------------


class TestBuildComponentFormFieldTypes:
    """Test that build_component_form maps each param type to the correct field."""

    def test_str_param_without_choices_creates_char_field(self):
        """Plain StrParam with no choices should produce a CharField."""
        FormClass = build_component_form(_StrParamComponent)
        assert isinstance(FormClass.base_fields["text"], forms.CharField)

    def test_str_param_with_choices_creates_choice_field(self):
        """StrParam with choices should produce a ChoiceField."""
        FormClass = build_component_form(_StrParamWithChoicesComponent)
        assert isinstance(FormClass.base_fields["size"], forms.ChoiceField)

    def test_bool_param_creates_typed_choice_field(self):
        """BoolParam should produce a TypedChoiceField (True/False dropdown)."""
        FormClass = build_component_form(_BoolParamComponent)
        assert isinstance(FormClass.base_fields["active"], forms.TypedChoiceField)

    def test_bool_css_class_param_creates_typed_choice_field(self):
        """BoolCSSClassParam (a BoolParam subclass) should also produce a TypedChoiceField."""
        FormClass = build_component_form(_BoolCSSClassParamComponent)
        assert isinstance(FormClass.base_fields["active"], forms.TypedChoiceField)

    def test_str_css_class_param_creates_choice_field(self):
        """StrCSSClassParam (always has choices) should produce a ChoiceField."""
        FormClass = build_component_form(_StrCSSClassParamComponent)
        assert isinstance(FormClass.base_fields["size"], forms.ChoiceField)

    def test_model_param_creates_model_choice_field(self):
        """ModelParam subclass (UserParam) should produce a ModelChoiceField."""
        FormClass = build_component_form(UserCardComponent)
        assert isinstance(FormClass.base_fields["user"], forms.ModelChoiceField)


# ---------------------------------------------------------------------------
# Field attributes
# ---------------------------------------------------------------------------


class TestBuildComponentFormFieldAttributes:
    """Test that generated fields carry the correct label, help_text and required."""

    def test_field_label_is_param_name(self):
        """Field label should be the parameter name."""
        FormClass = build_component_form(_StrParamComponent)
        assert FormClass.base_fields["text"].label == "text"

    def test_field_help_text_is_param_description(self):
        """Field help_text should be the parameter description string."""
        FormClass = build_component_form(_StrParamComponent)
        assert FormClass.base_fields["text"].help_text == "Some text."

    def test_char_field_not_required(self):
        """CharField derived from StrParam should never be required on the form."""
        FormClass = build_component_form(_StrParamComponent)
        assert FormClass.base_fields["text"].required is False

    def test_bool_field_not_required(self):
        """TypedChoiceField derived from BoolParam should never be required on the form."""
        FormClass = build_component_form(_BoolParamComponent)
        assert FormClass.base_fields["active"].required is False

    def test_choice_field_not_required(self):
        """ChoiceField derived from StrParam with choices should not be required."""
        FormClass = build_component_form(_StrParamWithChoicesComponent)
        assert FormClass.base_fields["size"].required is False

    def test_model_choice_field_not_required(self):
        """ModelChoiceField should never be required on the form."""
        FormClass = build_component_form(UserCardComponent)
        assert FormClass.base_fields["user"].required is False


# ---------------------------------------------------------------------------
# Choice field options
# ---------------------------------------------------------------------------


class TestChoiceFieldOptions:
    """Test that ChoiceField choices are built correctly."""

    def test_optional_choice_field_has_blank_option(self):
        """Optional StrParam with choices should include a leading blank ('—') option."""
        FormClass = build_component_form(_StrParamWithChoicesComponent)
        choices = FormClass.base_fields["size"].choices
        assert choices[0] == ("", "—")

    def test_required_choice_field_has_no_blank_option(self):
        """Required StrParam with choices should NOT include a leading blank option."""
        FormClass = build_component_form(_RequiredStrParamWithChoicesComponent)
        choices = FormClass.base_fields["size"].choices
        assert choices[0][0] != ""

    def test_choice_values_match_param_choices(self):
        """The non-blank choice values should match the spec's choices list."""
        FormClass = build_component_form(_StrParamWithChoicesComponent)
        choices = FormClass.base_fields["size"].choices
        non_blank_values = [c[0] for c in choices if c[0]]
        assert non_blank_values == ["sm", "md", "lg"]


# ---------------------------------------------------------------------------
# ModelChoiceField queryset
# ---------------------------------------------------------------------------


class TestModelChoiceFieldQueryset:
    """Test that the ModelChoiceField queryset is correctly configured."""

    def test_model_choice_field_has_queryset(self):
        """ModelChoiceField should have a queryset configured."""
        FormClass = build_component_form(UserCardComponent)
        assert FormClass.base_fields["user"].queryset is not None

    def test_model_choice_field_queryset_limited(self):
        """Queryset should be sliced to at most 10 results."""
        FormClass = build_component_form(UserCardComponent)
        field = FormClass.base_fields["user"]
        # A sliced queryset has high_mark set; verify it does not exceed 10.
        assert field.queryset.query.high_mark == 10


# ---------------------------------------------------------------------------
# Form class name
# ---------------------------------------------------------------------------


class TestBuildComponentFormClass:
    """Test properties of the generated form class itself."""

    def test_form_class_name(self):
        """The generated class should always be named ComponentParametersForm."""
        FormClass = build_component_form(_StrParamComponent)
        assert FormClass.__name__ == "ComponentParametersForm"

    def test_form_is_subclass_of_forms_form(self):
        """The generated class should be a proper Django Form subclass."""
        FormClass = build_component_form(_StrParamComponent)
        assert issubclass(FormClass, forms.Form)

    def test_parameterless_component_yields_empty_form(self):
        """A component with no params should produce a form with no fields."""

        class _NoParamComponent(TagComponent):
            """A component with no parameters."""

            template_format_str = "<div></div>"

        FormClass = build_component_form(_NoParamComponent)
        assert FormClass.base_fields == {}


# ---------------------------------------------------------------------------
# Block component content field
# ---------------------------------------------------------------------------


class TestBlockComponentContentField:
    """Test that BlockComponent subclasses get a content textarea field."""

    def test_content_field_added_for_block_component(self):
        """build_component_form should prepend a content field for BlockComponents."""
        from dj_design_system.components import BlockComponent

        class _SimpleBlockComponent(BlockComponent):
            """A minimal block component."""

            template_format_str = "<div>{content}</div>"

        FormClass = build_component_form(_SimpleBlockComponent)
        assert "content" in FormClass.base_fields

    def test_content_field_is_char_field_with_textarea(self):
        """The content field should use a Textarea widget."""
        from dj_design_system.components import BlockComponent

        class _SimpleBlockComponent(BlockComponent):
            """A minimal block component."""

            template_format_str = "<div>{content}</div>"

        FormClass = build_component_form(_SimpleBlockComponent)
        field = FormClass.base_fields["content"]
        assert isinstance(field, forms.CharField)
        assert isinstance(field.widget, forms.Textarea)

    def test_content_field_is_first(self):
        """The content field should come before declared param fields."""
        from dj_design_system.components import BlockComponent

        class _BlockWithParam(BlockComponent):
            """A block component with an extra param."""

            template_format_str = "<div class='{variant}'>{content}</div>"
            variant = StrParam("Variant style.", required=False)

        FormClass = build_component_form(_BlockWithParam)
        field_names = list(FormClass.base_fields.keys())
        assert field_names[0] == "content"
        assert "variant" in field_names

    def test_tag_component_has_no_content_field(self):
        """Regular TagComponent forms should not include a content field."""
        FormClass = build_component_form(_StrParamComponent)
        assert "content" not in FormClass.base_fields
