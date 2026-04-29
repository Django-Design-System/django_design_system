import pytest

from dj_design_system.components import TagComponent
from dj_design_system.parameters.base import (
    StrParam,
    generate_bool_css_class,
    generate_str_css_class,
)
from dj_design_system.parameters.field import FieldParam
from dj_design_system.parameters.model import ModelParam


# ---------------------------------------------------------------------------
# Helpers – a plain Python class used as the "model" for non-Django tests.
# ---------------------------------------------------------------------------


class FakeUser:
    """Minimal stub that looks like a user for parameter tests."""

    class _meta:  # noqa: N801
        @staticmethod
        def get_fields():
            return []

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeUserParam(ModelParam):
    """Concrete ModelParam backed by the plain FakeUser class."""

    class Meta:
        model = FakeUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_superuser",
            "role",
        ]
        bool_css_classes = [("is_active", "active"), "is_superuser"]
        str_css_classes = [("first_name", "name"), "role"]


# ---------------------------------------------------------------------------
# Meta validation
# ---------------------------------------------------------------------------


class TestModelParamMetaValidation:
    def test_missing_model_raises(self):
        with pytest.raises(ValueError, match="must define a 'model'"):

            class BadParam(ModelParam):
                class Meta:
                    model = None
                    fields = ["x"]

    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="must define a 'fields'"):

            class BadParam(ModelParam):
                class Meta:
                    model = FakeUser
                    fields = None

    def test_missing_meta_raises(self):
        with pytest.raises(ValueError, match="must define a Meta class"):

            class BadParam(ModelParam):
                pass

    def test_abstract_meta_skips_validation(self):
        """A subclass with Meta.abstract = True skips model/fields validation."""

        class IntermediateParam(ModelParam):
            class Meta:
                abstract = True

        assert issubclass(IntermediateParam, ModelParam)

    def test_bool_css_class_not_in_fields_raises(self):
        with pytest.raises(ValueError, match="bool_css_classes references 'hidden'"):

            class BadParam(ModelParam):
                class Meta:
                    model = FakeUser
                    fields = ["first_name"]
                    bool_css_classes = ["hidden"]

    def test_str_css_class_not_in_fields_raises(self):
        with pytest.raises(ValueError, match="str_css_classes references 'secret'"):

            class BadParam(ModelParam):
                class Meta:
                    model = FakeUser
                    fields = ["first_name"]
                    str_css_classes = [("secret", "s")]

    def test_css_class_tuple_attr_not_in_fields_raises(self):
        with pytest.raises(ValueError, match="bool_css_classes references 'missing'"):

            class BadParam(ModelParam):
                class Meta:
                    model = FakeUser
                    fields = ["email"]
                    bool_css_classes = [("missing", "gone")]

    def test_css_class_validation_skipped_for_all_fields(self):
        """When fields is '__all__', CSS class field validation is deferred to runtime."""

        class AllFieldsParam(ModelParam):
            class Meta:
                model = FakeUser
                fields = "__all__"
                bool_css_classes = ["anything"]

        assert issubclass(AllFieldsParam, ModelParam)


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------


class TestModelResolution:
    def test_resolve_class_reference(self):
        param = FakeUserParam("A user")
        param.__set_name__(None, "user")
        assert param._resolve_model() is FakeUser

    @pytest.mark.django_db
    def test_resolve_string_reference(self):
        """String references are resolved via Django's app registry."""
        from django.conf import settings

        class StringRefParam(ModelParam):
            class Meta:
                model = settings.AUTH_USER_MODEL
                fields = ["email"]

        param = StringRefParam("A user")
        param.__set_name__(None, "user")
        resolved = param._resolve_model()
        assert resolved.__name__ == "User"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestModelParamValidation:
    def test_valid_instance_accepted(self):
        param = FakeUserParam("A user")
        param.__set_name__(None, "user")
        fake = FakeUser(first_name="Ada")
        param.validate(fake)  # should not raise

    def test_invalid_type_rejected(self):
        param = FakeUserParam("A user")
        param.__set_name__(None, "user")
        with pytest.raises(TypeError, match="Expected FakeUser"):
            param.validate("not a user")


# ---------------------------------------------------------------------------
# Extra context (flattened attributes)
# ---------------------------------------------------------------------------


class TestGetExtraContext:
    def test_flattens_fields_into_context(self):
        param = FakeUserParam("A user")
        param.__set_name__(None, "user")
        fake = FakeUser(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            is_active=True,
            is_superuser=False,
            role="staff",
        )
        ctx = param.get_extra_context("user", fake)
        assert ctx == {
            "user_first_name": "Ada",
            "user_last_name": "Lovelace",
            "user_email": "ada@example.com",
            "user_is_active": True,
            "user_is_superuser": False,
            "user_role": "staff",
        }

    def test_none_value_returns_empty(self):
        param = FakeUserParam("A user", required=False)
        param.__set_name__(None, "user")
        assert param.get_extra_context("user", None) == {}

    def test_missing_attribute_returns_none(self):
        param = FakeUserParam("A user")
        param.__set_name__(None, "user")
        fake = FakeUser(first_name="Ada")  # missing last_name, email, is_active
        ctx = param.get_extra_context("user", fake)
        assert ctx["user_last_name"] is None
        assert ctx["user_email"] is None


# ---------------------------------------------------------------------------
# CSS classes
# ---------------------------------------------------------------------------


class TestGetCSSClasses:
    def test_bool_css_tuple(self):
        param = FakeUserParam("A user")
        param.__set_name__(None, "user")
        fake = FakeUser(is_active=True, is_superuser=False, first_name="", role="")
        classes = param.get_css_classes("user", fake)
        assert "user-active" in classes
        assert "user-is-superuser" not in classes

    def test_bool_css_string(self):
        param = FakeUserParam("A user")
        param.__set_name__(None, "user")
        fake = FakeUser(is_active=False, is_superuser=True, first_name="", role="")
        classes = param.get_css_classes("user", fake)
        assert "user-is-superuser" in classes
        assert "user-active" not in classes

    def test_str_css_tuple(self):
        param = FakeUserParam("A user")
        param.__set_name__(None, "user")
        fake = FakeUser(
            is_active=False, is_superuser=False, first_name="Andrew", role=""
        )
        classes = param.get_css_classes("user", fake)
        assert "user-name-Andrew" in classes

    def test_str_css_string(self):
        param = FakeUserParam("A user")
        param.__set_name__(None, "user")
        fake = FakeUser(
            is_active=False, is_superuser=False, first_name="", role="Employee"
        )
        classes = param.get_css_classes("user", fake)
        assert "user-role-Employee" in classes

    def test_str_css_empty_value_skipped(self):
        param = FakeUserParam("A user")
        param.__set_name__(None, "user")
        fake = FakeUser(is_active=False, is_superuser=False, first_name="", role="")
        classes = param.get_css_classes("user", fake)
        assert not any(c.startswith("user-name") for c in classes)
        assert not any(c.startswith("user-role") for c in classes)

    def test_none_value_returns_empty(self):
        param = FakeUserParam("A user", required=False)
        param.__set_name__(None, "user")
        assert param.get_css_classes("user", None) == []

    def test_full_example_from_spec(self):
        """Reproduce the example from the feature spec."""
        param = FakeUserParam("A user")
        param.__set_name__(None, "user")
        fake = FakeUser(
            is_active=True,
            is_superuser=True,
            first_name="Andrew",
            role="Employee",
        )
        classes = param.get_css_classes("user", fake)
        assert classes == [
            "user-active",
            "user-is-superuser",
            "user-name-Andrew",
            "user-role-Employee",
        ]


# ---------------------------------------------------------------------------
# Docstring
# ---------------------------------------------------------------------------


class TestModelParamDocstring:
    def test_required_param_docstring(self):
        param = FakeUserParam("The user")
        param.__set_name__(None, "user")
        doc = param.docstring()
        assert doc == "user: FakeUser - The user"

    def test_optional_param_docstring(self):
        param = FakeUserParam("The user", required=False)
        param.__set_name__(None, "user")
        doc = param.docstring()
        assert doc == "user: Optional[FakeUser] - The user"


# ---------------------------------------------------------------------------
# Base BaseParam hooks (default behaviour)
# ---------------------------------------------------------------------------


class TestBaseParamHooks:
    """The base BaseParam's hooks should return empty structures."""

    def test_get_extra_context_empty(self):
        param = StrParam("Some string")
        param.__set_name__(None, "foo")
        assert param.get_extra_context("foo", "bar") == {}

    def test_get_css_classes_empty(self):
        param = StrParam("Some string")
        param.__set_name__(None, "foo")
        assert param.get_css_classes("foo", "bar") == []


# ---------------------------------------------------------------------------
# has_been_set
# ---------------------------------------------------------------------------


class TestHasBeenSet:
    def _make_component_class(self):
        class MyComponent(TagComponent):
            template_format_str = "<div>{title}</div>"
            title = StrParam("A title", required=False)
            subtitle = StrParam("A subtitle", required=False, default="default-sub")

        return MyComponent

    def test_returns_false_before_param_is_set(self):
        MyComponent = self._make_component_class()
        comp = MyComponent()
        assert MyComponent.title.has_been_set(comp) is False

    def test_returns_true_after_param_is_set(self):
        MyComponent = self._make_component_class()
        comp = MyComponent(title="Hello")
        assert MyComponent.title.has_been_set(comp) is True

    def test_default_does_not_count_as_set(self):
        """A param with a default value is not considered explicitly set."""
        MyComponent = self._make_component_class()
        comp = MyComponent()
        assert MyComponent.subtitle.has_been_set(comp) is False

    def test_independent_instances_are_tracked_separately(self):
        """Setting a param on one instance does not affect another."""
        MyComponent = self._make_component_class()
        comp_a = MyComponent(title="Set")
        comp_b = MyComponent()
        assert MyComponent.title.has_been_set(comp_a) is True
        assert MyComponent.title.has_been_set(comp_b) is False

    def test_validate_params_can_detect_mutually_exclusive_params(self):
        """has_been_set enables validate_params to enforce mutual exclusion."""

        class ExclusiveComponent(TagComponent):
            template_format_str = "<div>{foo}{bar}</div>"
            foo = StrParam("Foo param", required=False)
            bar = StrParam("Bar param", required=False)

            def validate_params(self):
                if type(self).foo.has_been_set(self) and type(self).bar.has_been_set(
                    self
                ):
                    raise ValueError("Cannot set both 'foo' and 'bar'.")

        with pytest.raises(ValueError, match="Cannot set both 'foo' and 'bar'."):
            ExclusiveComponent(foo="a", bar="b")

        # Setting only one should not raise
        ExclusiveComponent(foo="a")
        ExclusiveComponent(bar="b")


class TestCssClassHelpers:
    def test_generate_bool_css_class_normalizes_underscore_to_hyphen(self):
        assert generate_bool_css_class("is_superuser", True) == ["is-superuser"]

    def test_generate_str_css_class_normalizes_underscore_to_hyphen(self):
        assert generate_str_css_class("hover_dark") == ["hover-dark"]


# ---------------------------------------------------------------------------
# Integration: ModelParam inside a component
# ---------------------------------------------------------------------------


class TestModelParamInComponent:
    def test_component_renders_with_model_context(self):
        class CardComponent(TagComponent):
            template_format_str = "<div class='{classes}'>{person_first_name}</div>"
            person = FakeUserParam("A person")

        fake = FakeUser(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            is_active=True,
            is_superuser=False,
            role="",
        )
        card = CardComponent(person=fake)
        html = card.render()
        assert "Ada" in html
        assert "person-active" in html

    def test_component_classes_include_model_css(self):
        class CardComponent(TagComponent):
            template_format_str = "<div class='{classes}'>hi</div>"
            person = FakeUserParam("A person")

        fake = FakeUser(
            first_name="Bob",
            last_name="Smith",
            email="bob@example.com",
            is_active=True,
            is_superuser=True,
            role="Admin",
        )
        card = CardComponent(person=fake)
        classes = card.get_classes_string()
        assert "person-active" in classes
        assert "person-is-superuser" in classes
        assert "person-name-Bob" in classes
        assert "person-role-Admin" in classes


# ---------------------------------------------------------------------------
# Integration: UserParam + UserCardComponent (requires Django DB)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUserCardComponent:
    def test_render_active_user(self):
        from django.contrib.auth import get_user_model

        from example_project.demo_components.components.user_card import (
            UserCardComponent,
        )

        User = get_user_model()
        user = User(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            is_active=True,
        )
        card = UserCardComponent(user=user)
        html = card.render()
        assert "Ada" in html
        assert "Lovelace" in html
        assert "ada@example.com" in html
        assert "user-active" in html

    def test_render_inactive_user(self):
        from django.contrib.auth import get_user_model

        from example_project.demo_components.components.user_card import (
            UserCardComponent,
        )

        User = get_user_model()
        user = User(
            first_name="Bob",
            last_name="Smith",
            email="bob@example.com",
            is_active=False,
        )
        card = UserCardComponent(user=user)
        html = card.render()
        assert "Bob" in html
        assert "user-active" not in html

    def test_user_parameter_rejects_non_user(self):
        from dj_design_system.parameters.user import UserParam

        param = UserParam("A user")
        param.__set_name__(None, "user")
        with pytest.raises(TypeError, match="Expected User"):
            param.validate("not a user")


# ---------------------------------------------------------------------------
# FieldParam
# ---------------------------------------------------------------------------


class HTMLRenderable:
    """Minimal stub that exposes __html__ like a Django BoundField."""

    def __init__(self, html: str):
        self._html = html

    def __html__(self) -> str:
        return self._html


class TestFieldParamValidation:
    def _make_param(self, **kwargs):
        param = FieldParam("A bound field", **kwargs)
        param.__set_name__(None, "field")
        return param

    def test_html_renderable_is_accepted(self):
        """An object with __html__ passes validation without raising."""
        param = self._make_param()
        param.validate(HTMLRenderable("<input>"))  # must not raise

    def test_none_is_accepted(self):
        """None is always accepted (handles optional fields)."""
        param = self._make_param(required=False)
        param.validate(None)  # must not raise

    def test_plain_string_is_rejected(self):
        """A plain string has no __html__ method and must be rejected."""
        param = self._make_param()
        with pytest.raises(ValueError, match="__html__"):
            param.validate("<input>")

    def test_integer_is_rejected(self):
        """An integer has no __html__ and must be rejected."""
        param = self._make_param()
        with pytest.raises(ValueError, match="int"):
            param.validate(42)

    def test_error_message_names_the_bad_type(self):
        """The ValueError message includes the actual type name for debugging."""

        class NotAField:
            pass

        param = self._make_param()
        with pytest.raises(ValueError, match="NotAField"):
            param.validate(NotAField())


class TestFieldParamType:
    def test_type_is_object(self):
        """FieldParam.type is ``object`` (duck-typed, not a specific class)."""
        assert FieldParam.type is object


class TestFieldParamDocstring:
    def test_docstring_with_description(self):
        param = FieldParam("The form field")
        param.__set_name__(None, "field")
        assert param.docstring() == "field: Optional[HTML-renderable] - The form field"

    def test_docstring_without_description(self):
        param = FieldParam()
        param.__set_name__(None, "widget")
        assert param.docstring() == "widget: Optional[HTML-renderable]"


class TestFieldParamInComponent:
    def test_component_renders_with_html_renderable(self):
        """FieldParam integrates with TagComponent and embeds the HTML output."""

        class FormComponent(TagComponent):
            template_format_str = "<div class='{classes}'>{field}</div>"
            field = FieldParam("A bound field")

        renderable = HTMLRenderable("<input type='text'>")
        comp = FormComponent(field=renderable)
        html = comp.render()
        assert "<input type='text'>" in html

    def test_component_rejects_plain_string_at_construction(self):
        """Passing a plain string to a FieldParam component raises ValueError."""

        class FormComponent(TagComponent):
            template_format_str = "<div>{field}</div>"
            field = FieldParam("A bound field")

        with pytest.raises(ValueError, match="__html__"):
            FormComponent(field="<input>")


# ---------------------------------------------------------------------------
# BaseParam.validate — error branches
# ---------------------------------------------------------------------------


class TestBaseParamValidate:
    def test_wrong_type_raises(self):
        p = StrParam("test")
        p.name = "p"
        with pytest.raises(ValueError, match="Expected.*str"):
            p.validate(123)

    def test_empty_choices_raises(self):
        p = StrParam("test")
        p.name = "p"
        p.choices = []
        with pytest.raises(ValueError, match="Choices must not be empty"):
            p.validate("anything")

    def test_wrong_choice_raises(self):
        p = StrParam("test", choices=["a", "b"])
        p.name = "p"
        with pytest.raises(ValueError, match="Expected one of"):
            p.validate("c")


# ---------------------------------------------------------------------------
# BaseParam.docstring and __str__
# ---------------------------------------------------------------------------


class TestBaseParamDocstring:
    def test_required_param(self):
        p = StrParam("my description")
        p.name = "my_param"
        result = p.docstring()
        assert "my_param: str" in result
        assert "my description" in result

    def test_optional_with_default(self):
        p = StrParam("my description", required=False, default="hello")
        p.name = "my_param"
        result = p.docstring()
        assert "Optional[str]" in result
        assert "default: hello" in result

    def test_no_description(self):
        p = StrParam(required=False)
        p.name = "my_param"
        result = p.docstring()
        assert "my_param" in result
        assert " - " not in result

    def test_str_representation(self):
        p = StrParam("test")
        p.name = "my_param"
        assert "my_param" in str(p)
        assert "str" in str(p)
