"""Tests for settings helpers."""

from django.test import override_settings

from dj_design_system.settings import get_default_background


class TestGetDefaultBackground:
    def test_returns_matching_background(self):
        """Returns the dict for the configured default value."""
        bg = get_default_background()
        assert "value" in bg
        assert "label" in bg
        assert "color" in bg

    @override_settings(
        dj_design_system={
            "GALLERY_CANVAS_BACKGROUNDS": {
                "warm": {"label": "Warm", "color": "#fff1e0"}
            },
            "GALLERY_CANVAS_DEFAULT_BACKGROUND": "nonexistent",
        }
    )
    def test_fallback_to_first_when_default_not_found(self):
        """Falls back to first background when default value is not in the list."""
        bg = get_default_background()
        assert bg["value"] == "warm"

    @override_settings(
        dj_design_system={
            "GALLERY_CANVAS_BACKGROUNDS": {},
            "GALLERY_CANVAS_EXTRA_BACKGROUNDS": {},
            "GALLERY_CANVAS_DEFAULT_BACKGROUND": "nonexistent",
        }
    )
    def test_fallback_to_hardcoded_when_no_backgrounds(self):
        """Falls back to hard-coded light-grey when no backgrounds are configured."""
        bg = get_default_background()
        assert bg["value"] == "light-grey"
        assert bg["color"] == "#f0f0f0"
