import pytest

from dj_design_system.components import TagComponent
from dj_design_system.parameters.base import StrParam


# ---------------------------------------------------------------------------
# Helpers – minimal concrete component for constraint testing.
# ---------------------------------------------------------------------------


class TwoParamComponent(TagComponent):
    """Component with two optional params for constraint testing."""

    template_format_str = "<div>{foo}{bar}</div>"
    foo = StrParam("Foo param", required=False)
    bar = StrParam("Bar param", required=False)
    baz = StrParam("Baz param", required=False)


# ---------------------------------------------------------------------------
# Meta.mutually_exclusive
# ---------------------------------------------------------------------------


class TestMutuallyExclusive:
    def test_raises_when_both_params_set(self):
        class ExclusiveComponent(TwoParamComponent):
            class Meta:
                mutually_exclusive = [("foo", "bar")]

        with pytest.raises(ValueError, match="'foo' and 'bar' cannot both be set"):
            ExclusiveComponent(foo="a", bar="b")

    def test_does_not_raise_when_only_first_set(self):
        class ExclusiveComponent(TwoParamComponent):
            class Meta:
                mutually_exclusive = [("foo", "bar")]

        ExclusiveComponent(foo="a")  # should not raise

    def test_does_not_raise_when_only_second_set(self):
        class ExclusiveComponent(TwoParamComponent):
            class Meta:
                mutually_exclusive = [("foo", "bar")]

        ExclusiveComponent(bar="b")  # should not raise

    def test_does_not_raise_when_neither_set(self):
        class ExclusiveComponent(TwoParamComponent):
            class Meta:
                mutually_exclusive = [("foo", "bar")]

        ExclusiveComponent()  # should not raise

    def test_multiple_pairs_all_checked(self):
        """All pairs in mutually_exclusive are enforced independently."""

        class ExclusiveComponent(TwoParamComponent):
            class Meta:
                mutually_exclusive = [("foo", "bar"), ("foo", "baz")]

        with pytest.raises(ValueError, match="'foo' and 'baz' cannot both be set"):
            ExclusiveComponent(foo="a", baz="c")

    def test_unknown_param_name_raises_at_class_definition(self):
        with pytest.raises(
            ValueError, match="mutually_exclusive references unknown param 'missing'"
        ):

            class BadComponent(TwoParamComponent):
                class Meta:
                    mutually_exclusive = [("foo", "missing")]


# ---------------------------------------------------------------------------
# Meta.requires
# ---------------------------------------------------------------------------


class TestRequires:
    def test_raises_when_dependent_set_without_dependency(self):
        class RequiresComponent(TwoParamComponent):
            class Meta:
                requires = [("bar", "foo")]

        with pytest.raises(ValueError, match="'bar' requires 'foo' to also be set"):
            RequiresComponent(bar="b")

    def test_does_not_raise_when_both_set(self):
        class RequiresComponent(TwoParamComponent):
            class Meta:
                requires = [("bar", "foo")]

        RequiresComponent(bar="b", foo="a")  # should not raise

    def test_does_not_raise_when_neither_set(self):
        class RequiresComponent(TwoParamComponent):
            class Meta:
                requires = [("bar", "foo")]

        RequiresComponent()  # should not raise

    def test_does_not_raise_when_only_dependency_set(self):
        """Setting the dependency alone (without the dependent) is always valid."""

        class RequiresComponent(TwoParamComponent):
            class Meta:
                requires = [("bar", "foo")]

        RequiresComponent(foo="a")  # should not raise

    def test_multiple_requires_all_checked(self):
        class RequiresComponent(TwoParamComponent):
            class Meta:
                requires = [("bar", "foo"), ("baz", "foo")]

        with pytest.raises(ValueError, match="'baz' requires 'foo' to also be set"):
            RequiresComponent(baz="c")

    def test_unknown_param_name_raises_at_class_definition(self):
        with pytest.raises(
            ValueError, match="requires references unknown param 'missing'"
        ):

            class BadComponent(TwoParamComponent):
                class Meta:
                    requires = [("foo", "missing")]


# ---------------------------------------------------------------------------
# Interaction with validate_params override hook
# ---------------------------------------------------------------------------


class TestConstraintsAndValidateParamsHook:
    def test_meta_constraints_checked_before_validate_params_hook(self):
        """Meta constraints fire before validate_params so the hook sees a valid state."""
        calls = []

        class OrderedComponent(TwoParamComponent):
            class Meta:
                mutually_exclusive = [("foo", "bar")]

            def validate_params(self):
                calls.append("validate_params")

        # Valid instantiation — validate_params should run.
        OrderedComponent(foo="a")
        assert calls == ["validate_params"]

        # Invalid instantiation — ValueError from Meta constraint fires first.
        calls.clear()
        with pytest.raises(ValueError):
            OrderedComponent(foo="a", bar="b")
        assert calls == []  # validate_params was never reached

    def test_validate_params_hook_still_runs_when_constraints_pass(self):
        class StrictComponent(TwoParamComponent):
            class Meta:
                mutually_exclusive = [("foo", "bar")]

            def validate_params(self):
                raise ValueError("hook fired")

        with pytest.raises(ValueError, match="hook fired"):
            StrictComponent(foo="a")


# ---------------------------------------------------------------------------
# description property and docstring() class method
# ---------------------------------------------------------------------------


class TestComponentIntrospection:
    def test_description_returns_docstring(self):
        class DocumentedComponent(TagComponent):
            """This is the component description."""

            template_format_str = "<div></div>"

        assert DocumentedComponent().description == "This is the component description."

    def test_description_none_when_no_docstring(self):
        class UndocumentedComponent(TagComponent):
            template_format_str = "<div></div>"

        assert UndocumentedComponent().description is None

    def test_class_docstring_contains_class_doc_and_params(self):
        from dj_design_system.parameters.base import StrParam

        class DocComponent(TagComponent):
            """My component."""

            label = StrParam("The label")
            template_format_str = "<div>{label}</div>"

        result = DocComponent.docstring()
        assert "My component." in result
        assert "label" in result
