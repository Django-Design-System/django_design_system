from dj_design_system.services.media import (
    build_static_url,
    coerce_path_list,
    get_own_media,
)


# ---------------------------------------------------------------------------
# coerce_path_list service
# ---------------------------------------------------------------------------


class TestCoercePathList:
    def test_single_string_becomes_list(self):
        assert coerce_path_list("myapp/base.css") == ["myapp/base.css"]

    def test_list_is_returned_as_list(self):
        paths = ["myapp/a.css", "myapp/b.css"]
        assert coerce_path_list(paths) == paths

    def test_empty_list_returns_empty_list(self):
        assert coerce_path_list([]) == []


# ---------------------------------------------------------------------------
# get_own_media service
# ---------------------------------------------------------------------------


class TestGetOwnMedia:
    def test_returns_none_when_no_media_class(self):
        class MyComponent:
            pass

        assert get_own_media(MyComponent) is None

    def test_returns_none_for_inherited_media(self):
        class Parent:
            class Media:
                css = ["parent.css"]

        class Child(Parent):
            pass

        # Child has no own Media — inheritance should not count.
        assert get_own_media(Child) is None

    def test_reads_css_list(self):
        class MyComponent:
            class Media:
                css = ["a.css", "b.css"]

        m = get_own_media(MyComponent)
        assert m is not None
        assert m.css == ["a.css", "b.css"]
        assert m.js == []

    def test_reads_js_list(self):
        class MyComponent:
            class Media:
                js = ["a.js"]

        m = get_own_media(MyComponent)
        assert m is not None
        assert m.js == ["a.js"]

    def test_normalises_css_single_string(self):
        class MyComponent:
            class Media:
                css = "single.css"

        m = get_own_media(MyComponent)
        assert m is not None
        assert m.css == ["single.css"]

    def test_normalises_js_single_string(self):
        class MyComponent:
            class Media:
                js = "single.js"

        m = get_own_media(MyComponent)
        assert m is not None
        assert m.js == ["single.js"]

    def test_empty_media_class(self):
        class MyComponent:
            class Media:
                pass

        m = get_own_media(MyComponent)
        assert m is not None
        assert m.css == []
        assert m.js == []


# ---------------------------------------------------------------------------
# build_static_url service
# ---------------------------------------------------------------------------


class TestBuildStaticUrl:
    def test_top_level_component(self):
        url = build_static_url("myapp", "", "button", ".css")
        assert url == "myapp/components/button.css"

    def test_nested_component(self):
        url = build_static_url("myapp", "cards", "info_card", ".css")
        assert url == "myapp/components/cards/info_card.css"

    def test_deeply_nested_component(self):
        url = build_static_url("myapp", "cards.layouts", "hero", ".js")
        assert url == "myapp/components/cards/layouts/hero.js"
