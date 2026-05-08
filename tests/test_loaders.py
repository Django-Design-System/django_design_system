import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateDoesNotExist

from dj_design_system.components import TagComponent, BlockComponent
from dj_design_system.loaders import ComponentsTemplateLoader
from dj_design_system.parameters import StrParam
from dj_design_system.services.registry import ComponentRegistry
from dj_design_system.services.component import derive_relative_path


DEMO_COMPONENTS_DIR = (
    Path(__file__).parent.parent / "example_project" / "demo_components" / "components"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def loader():
    """Return a ComponentsTemplateLoader scoped to demo_components only."""
    demo_config = MagicMock(spec=AppConfig)
    demo_config.label = "demo_components"
    demo_config.path = str(
        Path(__file__).parent.parent / "example_project" / "demo_components"
    )

    with patch(
        "dj_design_system.loaders.apps.get_app_config",
        side_effect=lambda label: demo_config if label == "demo_components" else (_ for _ in ()).throw(LookupError(label)),
    ):
        yield ComponentsTemplateLoader(engine=None)


# ---------------------------------------------------------------------------
# ComponentsTemplateLoader
# ---------------------------------------------------------------------------


class TestComponentsTemplateLoader:
    def test_yields_origin_for_html_file(self, loader):
        sources = list(loader.get_template_sources(
            "demo_components/components/button/button.html"
        ))
        assert len(sources) == 1
        assert sources[0].name.endswith(os.path.join("button", "button.html"))

    def test_ignores_non_components_namespace(self, loader):
        sources = list(loader.get_template_sources(
            "demo_components/templates/button.html"
        ))
        assert sources == []

    def test_ignores_non_html_extension(self, loader):
        sources = list(loader.get_template_sources(
            "demo_components/components/button/button.css"
        ))
        assert sources == []

    def test_ignores_unknown_app(self, loader):
        sources = list(loader.get_template_sources(
            "unknown_app/components/button/button.html"
        ))
        assert sources == []

    def test_get_contents_returns_file_contents(self, loader):
        """get_contents reads the file at origin.name."""
        sources = list(loader.get_template_sources(
            "demo_components/components/button/button.html"
        ))
        assert sources, "expected at least one origin"
        contents = loader.get_contents(sources[0])
        assert "btn" in contents

    def test_get_contents_raises_for_missing_file(self, loader):
        sources = list(loader.get_template_sources(
            "demo_components/components/button/button.html"
        ))
        assert sources
        origin = sources[0]
        # Tamper with the path to simulate a missing file
        origin.name = origin.name.replace("button.html", "does_not_exist.html")
        with pytest.raises(TemplateDoesNotExist):
            loader.get_contents(origin)

    def test_ignores_path_with_too_few_parts(self, loader):
        sources = list(loader.get_template_sources("button.html"))
        assert sources == []


# ---------------------------------------------------------------------------
# _bind_template — error cases
# ---------------------------------------------------------------------------


class TestBindTemplateErrors:
    def _make_registry_and_discover(self, cls):
        """Run _bind_template via a minimal registry discover call."""
        import pkgutil
        from importlib import import_module
        from dj_design_system.data import ComponentInfo

        info = ComponentInfo(
            component_class=cls,
            name="test",
            app_label="test_app",
            relative_path="",
        )
        reg = ComponentRegistry()
        reg._bind_template(info)
        return info

    def test_format_str_and_colocated_html_raises(self, tmp_path):
        """A component with template_format_str + co-located HTML raises ImproperlyConfigured."""
        # Write a real .html file next to this temporary module
        html_file = tmp_path / "my_widget.html"
        html_file.write_text("<div>hello</div>")

        class MyWidgetComponent(TagComponent):
            template_format_str = "<div>{label}</div>"
            label = StrParam("Label")

        # Patch inspect.getfile to point at our tmp_path
        import inspect
        with patch.object(inspect, "getfile", return_value=str(tmp_path / "my_widget.py")):
            from dj_design_system.data import ComponentInfo
            info = ComponentInfo(
                component_class=MyWidgetComponent,
                name="my_widget",
                app_label="test_app",
                relative_path="",
            )
            reg = ComponentRegistry()
            with pytest.raises(ImproperlyConfigured, match="template_format_str"):
                reg._bind_template(info)

    def test_format_str_and_explicit_template_name_raises(self):
        """template_format_str + template_name defined on the same class raises."""
        class ConflictComponent(TagComponent):
            template_format_str = "<span>{label}</span>"
            template_name = "some/template.html"
            label = StrParam("Label")

        from dj_design_system.data import ComponentInfo
        info = ComponentInfo(
            component_class=ConflictComponent,
            name="conflict",
            app_label="test_app",
            relative_path="",
        )
        reg = ComponentRegistry()
        with pytest.raises(ImproperlyConfigured, match="template_format_str"):
            reg._bind_template(info)

    def test_no_conflict_when_only_format_str(self):
        """template_format_str alone is fine — no error, no _template_name set."""
        class FormatOnlyComponent(TagComponent):
            template_format_str = "<span>{label}</span>"
            label = StrParam("Label")

        from dj_design_system.data import ComponentInfo
        info = ComponentInfo(
            component_class=FormatOnlyComponent,
            name="format_only",
            app_label="test_app",
            relative_path="",
        )
        reg = ComponentRegistry()
        reg._bind_template(info)
        assert not hasattr(FormatOnlyComponent, "_template_name")


# ---------------------------------------------------------------------------
# _bind_template — resolution
# ---------------------------------------------------------------------------


class TestBindTemplateResolution:
    def test_explicit_template_name_is_set(self):
        """Explicit template_name is copied to _template_name."""
        class ExplicitComponent(TagComponent):
            template_name = "myapp/components/explicit.html"
            label = StrParam("Label")

        from dj_design_system.data import ComponentInfo
        info = ComponentInfo(
            component_class=ExplicitComponent,
            name="explicit",
            app_label="test_app",
            relative_path="",
        )
        reg = ComponentRegistry()
        reg._bind_template(info)
        assert ExplicitComponent._template_name == "myapp/components/explicit.html"

    def test_colocated_html_sets_template_name(self, tmp_path):
        """A co-located .html file results in _template_name being set."""
        html_file = tmp_path / "my_card.html"
        html_file.write_text("<div>card</div>")

        class MyCardComponent(TagComponent):
            label = StrParam("Label")

        import inspect
        with patch.object(inspect, "getfile", return_value=str(tmp_path / "my_card.py")):
            from dj_design_system.data import ComponentInfo
            info = ComponentInfo(
                component_class=MyCardComponent,
                name="my_card",
                app_label="test_app",
                relative_path="cards",
            )
            reg = ComponentRegistry()
            reg._bind_template(info)

        assert MyCardComponent._template_name == "test_app/components/cards/my_card.html"

    def test_explicit_template_name_wins_over_colocated(self, tmp_path):
        """When both explicit template_name and co-located HTML exist, explicit wins."""
        html_file = tmp_path / "my_thing.html"
        html_file.write_text("<p>co-located</p>")

        class MyThingComponent(TagComponent):
            template_name = "custom/path/my_thing.html"
            label = StrParam("Label")

        import inspect
        with patch.object(inspect, "getfile", return_value=str(tmp_path / "my_thing.py")):
            from dj_design_system.data import ComponentInfo
            info = ComponentInfo(
                component_class=MyThingComponent,
                name="my_thing",
                app_label="test_app",
                relative_path="",
            )
            reg = ComponentRegistry()
            reg._bind_template(info)

        assert MyThingComponent._template_name == "custom/path/my_thing.html"


# ---------------------------------------------------------------------------
# render() — integration: button uses HTML template
# ---------------------------------------------------------------------------


class TestHtmlTemplateRendering:
    def test_button_renders_via_html_template(self, registry_with_demo_components):
        """ButtonComponent (which has button.html) renders via the template loader."""
        from example_project.demo_components.components.button.button import ButtonComponent

        result = ButtonComponent(label="Click me").render()
        assert "btn" in result
        assert "Click me" in result
        # Rendered by template, not format_html — no curly-brace artefacts
        assert "{" not in result

    def test_button_template_name_was_set(self, registry_with_demo_components):
        """After discovery, ButtonComponent._template_name should be set."""
        from example_project.demo_components.components.button.button import ButtonComponent

        assert hasattr(ButtonComponent, "_template_name")
        assert ButtonComponent._template_name.endswith("button.html")

    def test_button_disabled_renders_attribute(self, registry_with_demo_components):
        """The disabled_attr context variable is rendered correctly."""
        from example_project.demo_components.components.button.button import ButtonComponent

        result = ButtonComponent(label="Del", disabled=True).render()
        assert "disabled" in result
