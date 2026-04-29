"""Tests for the gallery client-side search index builder."""

import pytest

from dj_design_system.data import ComponentInfo
from dj_design_system.services.navigation import (
    _build_navigation,
    build_search_index,
    strip_markdown,
)
from tests.conftest import (
    DEMO_NAV_COMPONENTS,
    make_info,
)


# ---------------------------------------------------------------------------
# _strip_markdown
# ---------------------------------------------------------------------------


class TestStripMarkdown:
    """Test that _strip_markdown returns clean plain text."""

    def test_plain_text_unchanged(self):
        assert strip_markdown("Hello world") == "Hello world"

    def test_heading_stripped(self):
        result = strip_markdown("# My Heading\n\nSome text.")
        assert "My Heading" in result
        assert "#" not in result

    def test_bold_stripped(self):
        result = strip_markdown("This is **bold** text.")
        assert "bold" in result
        assert "**" not in result

    def test_italic_stripped(self):
        result = strip_markdown("This is *italic* text.")
        assert "italic" in result
        assert "*" not in result

    def test_inline_code_stripped(self):
        result = strip_markdown("Use the `foo()` function.")
        assert "foo()" in result
        assert "`" not in result

    def test_fenced_code_block_stripped(self):
        result = strip_markdown("```python\nprint('hi')\n```\nEnd.")
        assert "End" in result
        assert "```" not in result

    def test_link_text_preserved(self):
        result = strip_markdown("[Click here](https://example.com)")
        assert "Click here" in result
        assert "https://example.com" not in result

    def test_table_content_preserved(self):
        md = "| Column A | Column B |\n|---|---|\n| foo | bar |"
        result = strip_markdown(md)
        assert "foo" in result
        assert "bar" in result

    def test_empty_string(self):
        assert strip_markdown("") == ""

    def test_whitespace_collapsed(self):
        result = strip_markdown("Line one\n\n\nLine two")
        assert "\n" not in result
        assert "Line one" in result
        assert "Line two" in result


# ---------------------------------------------------------------------------
# build_search_index — entry fields
# ---------------------------------------------------------------------------


class TestBuildSearchIndexFields:
    """Test that each entry has the correct fields and values."""

    def test_component_entry_has_required_keys(self):
        components = [make_info("button")]
        tree = _build_navigation(components)
        index = build_search_index(tree)

        assert len(index) == 1
        entry = index[0]
        assert set(entry.keys()) == {"label", "url", "type", "breadcrumb", "content"}

    def test_component_entry_label(self):
        components = [make_info("button")]
        tree = _build_navigation(components)
        index = build_search_index(tree)

        assert index[0]["label"] == "Button"

    def test_component_entry_type(self):
        components = [make_info("button")]
        tree = _build_navigation(components)
        index = build_search_index(tree)

        assert index[0]["type"] == "component"

    def test_component_entry_url_is_non_empty_string(self):
        components = [make_info("button")]
        tree = _build_navigation(components)
        index = build_search_index(tree)

        assert isinstance(index[0]["url"], str)
        assert index[0]["url"]

    def test_app_nodes_excluded(self):
        """Top-level APP nodes must not appear as index entries."""
        components = [make_info("button", app_label="my_app")]
        tree = _build_navigation(components)
        index = build_search_index(tree)

        types = [e["type"] for e in index]
        assert "app" not in types

    def test_folder_entry_type(self):
        components = [make_info("badge", relative_path="elements")]
        tree = _build_navigation(components)
        index = build_search_index(tree)

        folder_entries = [e for e in index if e["type"] == "folder"]
        assert len(folder_entries) == 1
        assert folder_entries[0]["label"] == "Elements"

    def test_folder_and_component_both_present(self):
        components = [make_info("badge", relative_path="elements")]
        tree = _build_navigation(components)
        index = build_search_index(tree)

        types = {e["type"] for e in index}
        assert types == {"folder", "component"}


# ---------------------------------------------------------------------------
# build_search_index — breadcrumbs
# ---------------------------------------------------------------------------


class TestBuildSearchIndexBreadcrumbs:
    """Test that breadcrumbs reflect the ancestor hierarchy."""

    def test_root_level_component_has_app_breadcrumb(self):
        components = [make_info("button")]
        tree = _build_navigation(components)
        index = build_search_index(tree)

        button = next(e for e in index if e["label"] == "Button")
        assert "Test app" in button["breadcrumb"]

    def test_nested_component_includes_folder_breadcrumb(self):
        components = [make_info("badge", relative_path="elements")]
        tree = _build_navigation(components)
        index = build_search_index(tree)

        badge = next(e for e in index if e["label"] == "Badge")
        assert "Elements" in badge["breadcrumb"]

    def test_folder_breadcrumb_contains_app(self):
        components = [make_info("badge", relative_path="elements")]
        tree = _build_navigation(components)
        index = build_search_index(tree)

        folder = next(e for e in index if e["type"] == "folder")
        assert "Test app" in folder["breadcrumb"]

    def test_deeply_nested_breadcrumb_chain(self):
        components = [make_info("hero", relative_path="cards.layouts")]
        tree = _build_navigation(components)
        index = build_search_index(tree)

        hero = next(e for e in index if e["label"] == "Hero")
        assert "Cards" in hero["breadcrumb"]


# ---------------------------------------------------------------------------
# build_search_index — content from docstrings
# ---------------------------------------------------------------------------


class TestBuildSearchIndexContent:
    """Test that component docstrings are included in the content field."""

    def test_component_docstring_in_content(self):
        cls = type(
            "BtnCls",
            (),
            {"__doc__": "A clickable button for form submission."},
        )
        info = ComponentInfo(
            component_class=cls, name="button", app_label="app", relative_path=""
        )
        tree = _build_navigation([info])
        index = build_search_index(tree)

        button = next(e for e in index if e["label"] == "Button")
        assert "clickable" in button["content"]
        assert "form submission" in button["content"]

    def test_component_without_docstring_has_empty_content(self):
        cls = type("BtnCls", (), {"__doc__": None})
        info = ComponentInfo(
            component_class=cls, name="button", app_label="app", relative_path=""
        )
        tree = _build_navigation([info])
        index = build_search_index(tree)

        button = next(e for e in index if e["label"] == "Button")
        assert button["content"] == ""

    def test_docstring_markdown_is_stripped(self):
        cls = type(
            "BtnCls",
            (),
            {"__doc__": "A **bold** description with `code`."},
        )
        info = ComponentInfo(
            component_class=cls, name="button", app_label="app", relative_path=""
        )
        tree = _build_navigation([info])
        index = build_search_index(tree)

        button = next(e for e in index if e["label"] == "Button")
        assert "**" not in button["content"]
        assert "`" not in button["content"]
        assert "bold" in button["content"]


# ---------------------------------------------------------------------------
# build_search_index — content from markdown files (fake_app_nav integration)
# ---------------------------------------------------------------------------


class TestBuildSearchIndexMarkdown:
    """Integration tests using fake_app_nav to verify markdown file content."""

    @pytest.fixture()
    def index(self, nav_registry):
        tree = _build_navigation(
            nav_registry.list_all(),
            app_component_paths={"demo_nav": DEMO_NAV_COMPONENTS},
        )
        return build_search_index(tree)

    def test_document_node_included(self, index):
        """design_guidelines.md at the root level appears as a document entry."""
        doc = next(
            (e for e in index if e["label"] == "Design guidelines"),
            None,
        )
        assert doc is not None
        assert doc["type"] == "document"

    def test_document_content_from_file(self, index):
        """Content of a standalone markdown file is indexed."""
        doc = next(e for e in index if e["label"] == "Design guidelines")
        assert "guidelines" in doc["content"].lower()

    def test_standalone_doc_in_subfolder_included(self, index):
        """accessibility.md inside icon/ appears as a document entry."""
        doc = next(
            (e for e in index if e["label"] == "Accessibility"),
            None,
        )
        assert doc is not None
        assert doc["type"] == "document"

    def test_standalone_doc_content(self, index):
        """Content of accessibility.md is indexed."""
        doc = next(e for e in index if e["label"] == "Accessibility")
        assert "screen readers" in doc["content"].lower()

    def test_index_md_content_included_in_folder_node(self, index):
        """elements/index.md content appears in the Elements folder entry."""
        elements = next(e for e in index if e["label"] == "Elements")
        assert "element" in elements["content"].lower()

    def test_icon_index_md_content_on_component_node(self, index):
        """elements/icon/index.md content appears on the Icon component entry."""
        icon = next(e for e in index if e["label"] == "Icon")
        assert "icon" in icon["content"].lower()

    def test_icon_docstring_also_in_content(self, index):
        """IconComponent docstring is also indexed alongside the index.md content."""
        icon = next(e for e in index if e["label"] == "Icon")
        # Docstring: "An icon — lives in elements/icon/ to test leaf-folder collapsing."
        assert "icon" in icon["content"].lower()

    def test_all_component_labels_present(self, index):
        """All six components in fake_app_nav have an entry in the index."""
        component_labels = {e["label"] for e in index if e["type"] == "component"}
        assert "Action button" in component_labels
        assert "Icon" in component_labels
        assert "Badge" in component_labels
        assert "Info card" in component_labels
        assert "Divider" in component_labels
        assert "Tooltip" in component_labels

    def test_no_app_node_in_index(self, index):
        """The top-level APP node is never emitted as an index entry."""
        assert all(e["type"] != "app" for e in index)

    def test_index_md_not_a_separate_entry(self, index):
        """index.md files are attached to their parent node, not listed separately."""
        labels = [e["label"] for e in index]
        assert "Index" not in labels

    def test_breadcrumb_for_accessibility_doc(self, index):
        """accessibility.md breadcrumb traces through Icon and Elements."""
        doc = next(e for e in index if e["label"] == "Accessibility")
        assert "Elements" in doc["breadcrumb"]
        assert "Icon" in doc["breadcrumb"]
