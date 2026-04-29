from dj_design_system.data import ComponentMedia
from example_project.demo_components.components.button.button import ButtonComponent
from example_project.demo_components.components.card.info_card import InfoCardComponent
from example_project.demo_components.components.rich_button import RichButtonComponent


# ---------------------------------------------------------------------------
# ComponentMedia unit tests
# ---------------------------------------------------------------------------


class TestComponentMedia:
    def test_default_is_empty(self):
        m = ComponentMedia()
        assert m.css == []
        assert m.js == []

    def test_bool_false_when_empty(self):
        assert not ComponentMedia()

    def test_bool_true_with_css(self):
        assert ComponentMedia(css=["a.css"])

    def test_bool_true_with_js(self):
        assert ComponentMedia(js=["a.js"])

    def test_merge_combines_lists(self):
        a = ComponentMedia(css=["a.css"], js=["a.js"])
        b = ComponentMedia(css=["b.css"], js=["b.js"])
        merged = a.merge(b)
        assert merged.css == ["a.css", "b.css"]
        assert merged.js == ["a.js", "b.js"]

    def test_merge_deduplicates(self):
        a = ComponentMedia(css=["shared.css", "a.css"])
        b = ComponentMedia(css=["shared.css", "b.css"])
        merged = a.merge(b)
        assert merged.css == ["shared.css", "a.css", "b.css"]

    def test_merge_self_first(self):
        a = ComponentMedia(css=["parent.css"])
        b = ComponentMedia(css=["child.css"])
        merged = a.merge(b)
        assert merged.css == ["parent.css", "child.css"]

    def test_merge_returns_new_instance(self):
        a = ComponentMedia(css=["a.css"])
        b = ComponentMedia(css=["b.css"])
        merged = a.merge(b)
        assert merged is not a
        assert merged is not b


# ---------------------------------------------------------------------------
# ComponentInfo.media — auto-discovery
# ---------------------------------------------------------------------------


class TestAutoDiscovery:
    def test_finds_colocated_css_and_js(self, registry_with_demo_components):
        """ButtonComponent has button.css and button.js next to it."""
        reg = registry_with_demo_components
        info = reg.get_info(ButtonComponent)
        media = info.media
        assert media.css == ["demo_components/components/button/button.css"]
        assert media.js == ["demo_components/components/button/button.js"]

    def test_no_files_returns_empty_media(self, registry_with_demo_components):
        """InfoCardComponent has no co-located CSS or JS."""
        reg = registry_with_demo_components
        info = reg.get_info(InfoCardComponent)
        media = info.media
        assert media.css == []
        assert media.js == []

    def test_media_is_falsy_when_empty(self, registry_with_demo_components):
        reg = registry_with_demo_components
        info = reg.get_info(InfoCardComponent)
        assert not info.media

    def test_media_is_truthy_when_files_exist(self, registry_with_demo_components):
        reg = registry_with_demo_components
        info = reg.get_info(ButtonComponent)
        assert info.media


# ---------------------------------------------------------------------------
# ComponentInfo.media — explicit Media class + auto-discovery
# ---------------------------------------------------------------------------


class TestMediaClassOverride:
    def _make_info(
        self,
        component_class,
        name="test_component",
        app_label="testapp",
        relative_path="",
    ):
        from dj_design_system.data import ComponentInfo

        return ComponentInfo(
            component_class=component_class,
            name=name,
            app_label=app_label,
            relative_path=relative_path,
        )

    def test_media_class_list_stored_verbatim(self):
        from dj_design_system.components import TagComponent

        class MyComponent(TagComponent):
            class Media:
                css = ["testapp/components/my.css"]
                js = ["testapp/components/my.js"]

        info = self._make_info(MyComponent)
        assert info.media.css == ["testapp/components/my.css"]
        assert info.media.js == ["testapp/components/my.js"]

    def test_media_class_single_string_normalised(self):
        from dj_design_system.components import TagComponent

        class MyComponent(TagComponent):
            class Media:
                css = "testapp/components/my.css"

        info = self._make_info(MyComponent)
        assert info.media.css == ["testapp/components/my.css"]

    def test_media_class_no_colocated_files(self):
        """A component with a Media class but no co-located files returns only
        the explicit Media entries."""
        from dj_design_system.components import TagComponent

        class ExplicitMediaComponent(TagComponent):
            class Media:
                css = ["explicit/path.css"]

        info = self._make_info(ExplicitMediaComponent)
        media = info.media
        assert media.css == ["explicit/path.css"]

    def test_media_class_merges_with_autodiscovery(self, registry_with_demo_components):
        """A component with both an explicit Media class and co-located files
        should include entries from both sources.

        RichButtonComponent declares ``Media.css = ["demo_components/components/rich_button_extras.css"]``
        and also has a co-located ``rich_button.css`` file. Both should appear
        in the merged result, with explicit entries first.
        """
        reg = registry_with_demo_components
        info = reg.get_info(RichButtonComponent)
        media = info.media
        assert any(p.endswith("rich_button_extras.css") for p in media.css)
        assert any(p.endswith("rich_button.css") for p in media.css)
        # Explicit entry appears before auto-discovered entry.
        extras_idx = next(
            i for i, p in enumerate(media.css) if p.endswith("rich_button_extras.css")
        )
        auto_idx = next(
            i
            for i, p in enumerate(media.css)
            if p.endswith("rich_button.css")
            and not p.endswith("rich_button_extras.css")
        )
        assert extras_idx < auto_idx

    def test_mro_merge_parent_first(self):
        from dj_design_system.components import TagComponent

        class ParentComponent(TagComponent):
            class Media:
                css = ["testapp/components/parent.css"]

        class ChildComponent(ParentComponent):
            class Media:
                css = ["testapp/components/child.css"]

        info = self._make_info(ChildComponent)
        assert info.media.css == [
            "testapp/components/parent.css",
            "testapp/components/child.css",
        ]

    def test_mro_merge_deduplicates(self):
        from dj_design_system.components import TagComponent

        class ParentComponent(TagComponent):
            class Media:
                css = ["testapp/components/shared.css", "testapp/components/parent.css"]

        class ChildComponent(ParentComponent):
            class Media:
                css = ["testapp/components/shared.css", "testapp/components/child.css"]

        info = self._make_info(ChildComponent)
        assert info.media.css == [
            "testapp/components/shared.css",
            "testapp/components/parent.css",
            "testapp/components/child.css",
        ]

    def test_parent_only_media_inherited_by_child(self):
        """Child without its own Media still inherits via the MRO merge."""
        from dj_design_system.components import TagComponent

        class ParentComponent(TagComponent):
            class Media:
                css = ["testapp/components/parent.css"]

        class ChildComponent(ParentComponent):
            pass

        info = self._make_info(ChildComponent)
        assert info.media.css == ["testapp/components/parent.css"]


# ---------------------------------------------------------------------------
# BaseComponent.get_media() integration
# ---------------------------------------------------------------------------


class TestGetMedia:
    def test_get_media_delegates_to_registry(self, registry_with_demo_components):
        from dj_design_system import component_registry

        reg = registry_with_demo_components

        # Temporarily swap the global registry so get_media() can resolve.
        original = component_registry._components[:]
        component_registry._components = reg._components

        try:
            media = ButtonComponent.get_media()
            assert media.css == ["demo_components/components/button/button.css"]
            assert media.js == ["demo_components/components/button/button.js"]
        finally:
            component_registry._components = original
