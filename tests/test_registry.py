from unittest.mock import patch

import pytest
from django import template

from dj_design_system.components import (
    BaseComponent,
    BlockComponent,
    TagComponent,
)
from dj_design_system.data import ComponentInfo, InvalidTagType
from dj_design_system.parameters import StrParam
from dj_design_system.services.component import derive_name
from dj_design_system.services.registry import (
    ComponentDoesNotExist,
    MultipleComponentsFound,
)
from dj_design_system.types import TagType
from example_project.demo_components.components.alert import AlertComponent
from example_project.demo_components.components.badge import BadgeComponent
from example_project.demo_components.components.button.button import ButtonComponent
from example_project.demo_components.components.card.info_card import InfoCardComponent
from example_project.demo_components.components.card.layouts.hero import (
    HeroCardComponent,
)
from example_project.demo_extra.components.button import (
    ButtonComponent as ButtonComponentB,
)
from example_project.demo_single.components import PillComponent


class TestDeriveName:
    """Test the derive_name helper that converts class names to component names."""

    def test_strips_component_suffix(self):
        class IconComponent:
            pass

        assert derive_name(IconComponent) == "icon"

    def test_camel_case_to_snake_case(self):
        class MyFancyButton:
            pass

        assert derive_name(MyFancyButton) == "my_fancy_button"

    def test_strips_component_and_converts(self):
        class HeroCardComponent:
            pass

        assert derive_name(HeroCardComponent) == "hero_card"

    def test_single_word_no_suffix(self):
        class Badge:
            pass

        assert derive_name(Badge) == "badge"

    def test_does_not_strip_when_name_is_component(self):
        """'Component' alone should not become an empty string."""

        class Component:
            pass

        assert derive_name(Component) == "component"

    def test_consecutive_uppercase(self):
        class HTMLRenderer:
            pass

        assert derive_name(HTMLRenderer) == "html_renderer"

    def test_single_letter_class(self):
        class X:
            pass

        assert derive_name(X) == "x"


class TestDiscovery:
    """Test that component discovery finds the right classes."""

    def test_discovers_top_level_component(self, registry_with_demo_components):
        reg = registry_with_demo_components
        classes = [c.component_class for c in reg.list_all()]
        assert BadgeComponent in classes

    def test_discovers_subfolder_component(self, registry_with_demo_components):
        reg = registry_with_demo_components
        classes = [c.component_class for c in reg.list_all()]
        assert ButtonComponent in classes

    def test_discovers_nested_component(self, registry_with_demo_components):
        reg = registry_with_demo_components
        classes = [c.component_class for c in reg.list_all()]
        assert InfoCardComponent in classes

    def test_discovers_deeply_nested_component(self, registry_with_demo_components):
        reg = registry_with_demo_components
        classes = [c.component_class for c in reg.list_all()]
        assert HeroCardComponent in classes

    def test_discovers_block_component(self, registry_with_demo_components):
        reg = registry_with_demo_components
        classes = [c.component_class for c in reg.list_all()]
        assert AlertComponent in classes

    def test_excludes_abstract_component(self, registry_with_demo_components):
        reg = registry_with_demo_components
        names = [c.name for c in reg.list_all()]
        assert "abstract_card" not in names

    def test_excludes_base_component(self, registry_with_demo_components):
        reg = registry_with_demo_components
        classes = [c.component_class for c in reg.list_all()]
        assert BaseComponent not in classes

    def test_excludes_block_component_base(self, registry_with_demo_components):
        reg = registry_with_demo_components
        classes = [c.component_class for c in reg.list_all()]
        assert BlockComponent not in classes

    def test_excludes_tag_component_base(self, registry_with_demo_components):
        reg = registry_with_demo_components
        classes = [c.component_class for c in reg.list_all()]
        assert TagComponent not in classes

    def test_expected_components_present(self, registry_with_demo_components):
        """demo_components has exactly these concrete components."""
        reg = registry_with_demo_components
        names = {info.name for info in reg.list_all()}
        assert names == {
            "button",
            "alert",
            "badge",
            "rich_button",
            "user_card",
            "info_card",
            "hero",
        }

    def test_single_file_components_module(self, registry_with_demo_single):
        reg = registry_with_demo_single
        names = {info.name for info in reg.list_all()}
        assert names == {"pill", "chip"}
        assert all(info.relative_path == "" for info in reg.list_all())


class TestComponentInfo:
    """Test that ComponentInfo fields are set correctly."""

    def test_app_label(self, registry_with_demo_components):
        reg = registry_with_demo_components
        for info in reg.list_all():
            assert info.app_label == "demo_components"

    def test_top_level_relative_path(self, registry_with_demo_components):
        """Badge is at the top level of components/ (relative_path='')."""
        reg = registry_with_demo_components
        info = reg.get_info(BadgeComponent)
        assert info.relative_path == ""

    def test_subfolder_relative_path(self, registry_with_demo_components):
        """Button lives in components/button/ (relative_path='button')."""
        reg = registry_with_demo_components
        info = reg.get_info(ButtonComponent)
        assert info.relative_path == "button"

    def test_nested_relative_path(self, registry_with_demo_components):
        reg = registry_with_demo_components
        info = reg.get_info(InfoCardComponent)
        assert info.relative_path == "card"

    def test_deeply_nested_relative_path(self, registry_with_demo_components):
        reg = registry_with_demo_components
        info = reg.get_info(HeroCardComponent)
        assert info.relative_path == "card.layouts"

    def test_auto_derived_name(self, registry_with_demo_components):
        reg = registry_with_demo_components
        info = reg.get_info(ButtonComponent)
        assert info.name == "button"

    def test_auto_derived_name_strips_component(self, registry_with_demo_components):
        reg = registry_with_demo_components
        info = reg.get_info(InfoCardComponent)
        assert info.name == "info_card"

    def test_custom_meta_name(self, registry_with_demo_components):
        reg = registry_with_demo_components
        info = reg.get_info(HeroCardComponent)
        assert info.name == "hero"

    def test_single_file_relative_path(self, registry_with_demo_single):
        reg = registry_with_demo_single
        info = reg.get_info(PillComponent)
        assert info.relative_path == ""
        assert info.name == "pill"


class TestGetByName:
    """Test get_by_name lookups."""

    def test_unique_name(self, registry_with_demo_components):
        reg = registry_with_demo_components
        info = reg.get_by_name("button")
        assert info.component_class is ButtonComponent

    def test_custom_name(self, registry_with_demo_components):
        reg = registry_with_demo_components
        info = reg.get_by_name("hero")
        assert info.component_class is HeroCardComponent

    def test_not_found_raises(self, registry_with_demo_components):
        reg = registry_with_demo_components
        with pytest.raises(ComponentDoesNotExist, match="nonexistent"):
            reg.get_by_name("nonexistent")

    def test_ambiguous_raises(self, registry_with_two_apps):
        reg = registry_with_two_apps
        with pytest.raises(MultipleComponentsFound, match="button"):
            reg.get_by_name("button")

    def test_disambiguate_with_app_label(self, registry_with_two_apps):
        reg = registry_with_two_apps
        info_a = reg.get_by_name("button", app_label="demo_components")
        assert info_a.component_class is ButtonComponent

        info_b = reg.get_by_name("button", app_label="demo_extra")
        assert info_b.component_class is ButtonComponentB

    def test_not_found_with_app_label(self, registry_with_demo_components):
        reg = registry_with_demo_components
        with pytest.raises(ComponentDoesNotExist, match="demo_components"):
            reg.get_by_name("nonexistent", app_label="demo_components")

        with pytest.raises(ComponentDoesNotExist, match="demo_extra"):
            reg.get_by_name("hero", app_label="demo_extra")


class TestGetInfo:
    """Test get_info lookups by class."""

    def test_returns_info(self, registry_with_demo_components):
        reg = registry_with_demo_components
        info = reg.get_info(ButtonComponent)
        assert info.component_class is ButtonComponent
        assert info.name == "button"

    def test_unregistered_raises(self, registry_with_demo_components):
        reg = registry_with_demo_components
        with pytest.raises(ComponentDoesNotExist):
            reg.get_info(BaseComponent)


class TestListByApp:
    """Test list_by_app filtering."""

    def test_returns_correct_app(self, registry_with_two_apps):
        reg = registry_with_two_apps
        components = reg.list_by_app("demo_components")
        assert len(components) == 7
        assert all(c.app_label == "demo_components" for c in components)

    def test_returns_other_app(self, registry_with_two_apps):
        reg = registry_with_two_apps
        extra = reg.list_by_app("demo_extra")
        assert len(extra) == 1
        assert extra[0].app_label == "demo_extra"

    def test_returns_empty_for_unknown_app(self, registry_with_demo_components):
        reg = registry_with_demo_components
        assert reg.list_by_app("nonexistent_app") == []


class TestBaseComponentHelpers:
    """Test the helper classmethods on BaseComponent."""

    def test_get_name(self, registry_with_demo_components):
        """Patch the module-level registry so the classmethod can find it."""
        reg = registry_with_demo_components
        with patch("dj_design_system.component_registry", reg):
            assert ButtonComponent.get_name() == "button"

    def test_get_app_label(self, registry_with_demo_components):
        reg = registry_with_demo_components
        with patch("dj_design_system.component_registry", reg):
            assert ButtonComponent.get_app_label() == "demo_components"

    def test_get_relative_path(self, registry_with_demo_components):
        reg = registry_with_demo_components
        with patch("dj_design_system.component_registry", reg):
            assert HeroCardComponent.get_relative_path() == "card.layouts"

    def test_get_name_custom_meta(self, registry_with_demo_components):
        reg = registry_with_demo_components
        with patch("dj_design_system.component_registry", reg):
            assert HeroCardComponent.get_name() == "hero"


class TestTagComponentAsTag:
    """Test TagComponent.as_tag() with and without Meta.positional_args."""

    def test_kwargs_only(self):
        """A TagComponent with no positional_args accepts only kwargs."""

        class NoPositionalComponent(TagComponent):
            template_format_str = "<div class='card {classes}'>A card</div>"

        tag_func = NoPositionalComponent.as_tag()
        result = str(tag_func())
        assert "A card" in result

    def test_single_positional_arg(self):
        """A TagComponent with positional_args maps positional to kwargs."""
        tag_func = ButtonComponent.as_tag()
        result = str(tag_func("Click me"))
        assert "Click me" in result

    def test_positional_arg_as_kwarg(self):
        """A declared positional arg can still be passed as a kwarg."""
        tag_func = ButtonComponent.as_tag()
        result = str(tag_func(label="Click me"))
        assert "Click me" in result

    def test_positional_args_not_inherited(self):
        """Subclasses do NOT inherit Meta.positional_args from parents."""

        class Parent(TagComponent):
            name = StrParam("Name.")

            class Meta:
                positional_args = ["name"]

        class Child(Parent):
            """No own Meta — should NOT inherit positional_args."""

            pass

        # Parent has positional_args
        parent_tag = Parent.as_tag()
        assert str(parent_tag("hello"))  # positional works

        # Child should NOT have positional_args
        assert Child.get_positional_args() == []
        child_tag = Child.as_tag()
        # kwargs still work (output won't contain "hello" without a real template,
        # but the important thing is no TypeError from unexpected positional arg)
        child_tag(name="hello")


class TestBlockComponentAsTag:
    """Test BlockComponent.as_tag() with content and Meta.positional_args."""

    def test_content_only(self):
        """A BlockComponent with no positional_args accepts content + kwargs."""

        class SimpleBlock(BlockComponent):
            template_format_str = "<div class='{classes}'>{content}</div>"

        tag_func = SimpleBlock.as_tag()
        result = str(tag_func("hello"))
        assert "hello" in result

    def test_content_with_positional_args(self):
        """A BlockComponent with positional_args maps them after content."""
        tag_func = AlertComponent.as_tag()
        result = str(tag_func("Watch out!", "warning"))
        assert "Watch out!" in result
        assert "warning" in result

    def test_content_with_kwargs(self):
        """A BlockComponent with positional_args can still use kwargs."""
        tag_func = AlertComponent.as_tag()
        result = str(tag_func("Watch out!", level="warning"))
        assert "Watch out!" in result
        assert "warning" in result


class TestQualifiedName:
    """Test ComponentInfo.qualified_name generation."""

    def test_top_level_component(self, registry_with_demo_components):
        """Top-level component: app_label__name."""
        reg = registry_with_demo_components
        info = reg.get_info(BadgeComponent)
        assert info.qualified_name == "demo_components__badge"

    def test_subfolder_component(self, registry_with_demo_components):
        """Component in a same-name subfolder: app_label__folder__name."""
        reg = registry_with_demo_components
        info = reg.get_info(ButtonComponent)
        assert info.qualified_name == "demo_components__button__button"

    def test_nested_component(self, registry_with_demo_components):
        """Nested component: app_label__path__name."""
        reg = registry_with_demo_components
        info = reg.get_info(InfoCardComponent)
        assert info.qualified_name == "demo_components__card__info_card"

    def test_deeply_nested_component(self, registry_with_demo_components):
        """Deeply nested component: app_label__path__path__name."""
        reg = registry_with_demo_components
        info = reg.get_info(HeroCardComponent)
        assert info.qualified_name == "demo_components__card__layouts__hero"

    def test_single_file_component(self, registry_with_demo_single):
        """Single-file component: app_label__name."""
        reg = registry_with_demo_single
        info = reg.get_info(PillComponent)
        assert info.qualified_name == "demo_single__pill"


class TestTagType:
    """Test ComponentInfo.tag_type detection."""

    def test_tag_component_returns_tag(self, registry_with_demo_components):
        """TagComponent subclass has tag_type=TagType.TAG."""
        reg = registry_with_demo_components
        info = reg.get_info(ButtonComponent)
        assert info.tag_type is TagType.TAG

    def test_block_component_returns_block(self, registry_with_demo_components):
        """BlockComponent subclass has tag_type=TagType.BLOCK."""
        reg = registry_with_demo_components
        info = reg.get_info(AlertComponent)
        assert info.tag_type is TagType.BLOCK

    def test_base_component_raises_invalid_tag_type(self):
        """Direct BaseComponent subclass raises InvalidTagType."""

        class PlainComponent(BaseComponent):
            pass

        info = ComponentInfo(
            component_class=PlainComponent,
            name="plain",
            app_label="test",
            relative_path="",
        )
        with pytest.raises(InvalidTagType):
            info.tag_type  # noqa B018


class TestRegisterTemplatetags:
    """Test register_templatetags() on a Django Template Library."""

    def test_unique_names_registered_as_short_and_qualified(
        self, registry_with_demo_components
    ):
        """Each unique name is registered both as short and qualified."""
        reg = registry_with_demo_components
        lib = template.Library()
        reg.register_templatetags(lib)

        assert "button" in lib.tags
        assert "demo_components__button__button" in lib.tags
        assert "hero" in lib.tags
        assert "demo_components__card__layouts__hero" in lib.tags

    def test_clashing_short_name_last_wins(self, registry_with_two_apps):
        """When short names clash, the last-discovered component wins."""
        reg = registry_with_two_apps
        lib = template.Library()
        reg.register_templatetags(lib)

        # Short name 'button' should be registered
        assert "button" in lib.tags
        # Qualified names should both exist
        assert "demo_components__button__button" in lib.tags
        assert "demo_extra__button" in lib.tags

        # The short name should resolve to the LAST discovered (demo_extra)
        short_tag_func = lib.tags["button"].__wrapped__
        result = str(short_tag_func())
        assert "btn-extra" in result

    def test_app_label_scoping(self, registry_with_two_apps):
        """When app_label is given, only that app's components are registered."""
        reg = registry_with_two_apps
        lib = template.Library()
        reg.register_templatetags(lib, app_label="demo_components")

        # 'button' should be unique within demo_components
        assert "button" in lib.tags
        assert "demo_components__button__button" in lib.tags
        # demo_extra components should NOT be registered
        assert "demo_extra__button" not in lib.tags

    def test_app_label_scoping_unique_within_app(self, registry_with_two_apps):
        """Each app's per-app library has button as a unique short name."""
        reg = registry_with_two_apps

        lib_a = template.Library()
        reg.register_templatetags(lib_a, app_label="demo_components")

        lib_b = template.Library()
        reg.register_templatetags(lib_b, app_label="demo_extra")

        # Both should have 'button' as a non-error tag
        assert "button" in lib_a.tags
        assert "button" in lib_b.tags

    def test_block_components_registered_as_block_tags(
        self, registry_with_demo_components
    ):
        """BlockComponent subclasses are registered via simple_block_tag."""
        reg = registry_with_demo_components
        lib = template.Library()
        reg.register_templatetags(lib)

        # AlertComponent is a BlockComponent — it should be registered
        assert "alert" in lib.tags
        assert "demo_components__alert" in lib.tags

    def test_abstract_components_not_registered(self, registry_with_demo_components):
        """Abstract components are excluded from the registry and templatetags."""
        reg = registry_with_demo_components
        lib = template.Library()
        reg.register_templatetags(lib)

        assert "abstract_card" not in lib.tags


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


class TestRegistryErrorPropagation:
    """Errors during module import should bubble up as ImportError."""

    def test_autodiscover_non_import_error_is_wrapped(self):
        """A components module that raises a non-ImportError wraps it in ImportError."""
        from unittest.mock import MagicMock, patch

        from dj_design_system.services.registry import ComponentRegistry

        broken_cfg = MagicMock()
        broken_cfg.name = "fake_broken_app"
        broken_cfg.label = "fake_broken_app"

        with patch(
            "dj_design_system.services.registry.import_module",
            side_effect=RuntimeError("something went wrong"),
        ):
            with patch("django.apps.apps.get_app_configs", return_value=[broken_cfg]):
                reg = ComponentRegistry()
                with pytest.raises(ImportError, match="something went wrong"):
                    reg.autodiscover()

    def test_iter_submodules_non_import_error_is_wrapped(self):
        """A submodule that raises a non-ImportError is wrapped in ImportError."""
        import pkgutil
        from unittest.mock import MagicMock, patch

        from dj_design_system.services.registry import ComponentRegistry

        reg = ComponentRegistry()
        fake_module = MagicMock()
        fake_module.__name__ = "fakeapp.components"
        fake_module.__path__ = ["fake/path"]

        fake_iter = [(None, "fakeapp.components.widget", False)]
        with (
            patch.object(pkgutil, "walk_packages", return_value=fake_iter),
            patch(
                "dj_design_system.services.registry.import_module",
                side_effect=RuntimeError("bad submodule"),
            ),
        ):
            with pytest.raises(ImportError, match="bad submodule"):
                list(reg._iter_app_submodules(fake_module, "fakeapp.components"))
