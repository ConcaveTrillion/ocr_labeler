from __future__ import annotations

import pytest

from ocr_labeler.state.ground_truth import find_ground_truth_text

# ocr_labeler/state/test_ground_truth.py


# Relative import of the code under test


# ------------- Tests --------------


@pytest.mark.parametrize(
    "name, ground_truth_map, expected",
    [
        # Exact match
        ("001.png", {"001.png": "text1"}, "text1"),
        # Lowercase match
        ("001.PNG", {"001.png": "text1"}, "text1"),
        # Base name match (with extension)
        ("001.png", {"001": "text1"}, "text1"),
        # Lowercase base match
        ("001.PNG", {"001": "text1"}, "text1"),
        # No match
        ("002.png", {"001.png": "text1"}, None),
        # Empty name
        ("", {"001.png": "text1"}, None),
        # Name without extension, exact match
        ("001", {"001": "text1"}, "text1"),
        # Name without extension, lowercase match
        ("001", {"001": "text1"}, "text1"),  # Same as above
        # Name with multiple dots (e.g., file.tar.gz)
        ("file.tar.gz", {"file.tar": "text1"}, "text1"),
        # Case where base is matched
        ("file.TAR.GZ", {"file.tar": "text1"}, "text1"),
        # No extension, no match
        ("002", {"001": "text1"}, None),
        # Extension present, but only original matches
        (
            "001.png",
            {"001.png": "text1", "001": "text2"},
            "text1",
        ),  # Prioritizes original
        # Lowercase prioritized after original
        ("001.PNG", {"001.png": "text1", "001": "text2"}, "text1"),
        # Base after lowercase
        ("001.png", {"001.png": "text1", "001": "text2"}, "text1"),
    ],
)
def test_find_ground_truth_text_variants(name, ground_truth_map, expected):
    """Test find_ground_truth_text with various name variants and map contents."""
    result = find_ground_truth_text(name, ground_truth_map)
    assert result == expected


def test_find_ground_truth_text_no_candidates():
    """Test with empty ground_truth_map."""
    result = find_ground_truth_text("001.png", {})
    assert result is None


def test_find_ground_truth_text_deduplication():
    """Test that candidates are deduplicated, e.g., if name == name.lower()."""
    ground_truth_map = {"test": "text1"}
    # Name where lower is same as original
    result = find_ground_truth_text("test", ground_truth_map)
    assert result == "text1"
    # Should not check twice (though hard to assert directly, ensure no error)


def test_find_ground_truth_text_priority_order():
    """Test priority: original, lowercase, base, lowercase base."""
    ground_truth_map = {
        "001.png": "original",
        "001": "base",
    }
    # Original should win
    result = find_ground_truth_text("001.png", ground_truth_map)
    assert result == "original"

    # If original not present, base
    ground_truth_map.pop("001.png")
    result = find_ground_truth_text("001.png", ground_truth_map)
    assert result == "base"


def test_find_ground_truth_text_case_insensitive_base():
    """Test case insensitive lookup for base name."""
    ground_truth_map = {"001": "text1"}
    result = find_ground_truth_text("001.PNG", ground_truth_map)
    assert result == "text1"


def test_find_ground_truth_text_no_extension_no_base():
    """Test name without extension, only tries name and lowercase."""
    ground_truth_map = {"001": "text1"}
    result = find_ground_truth_text("001", ground_truth_map)
    assert result == "text1"

    # Lowercase
    ground_truth_map = {"001": "text1"}
    result = find_ground_truth_text(
        "001", ground_truth_map
    )  # Assuming map has lower if needed, but in this case same
    assert result == "text1"

    # No match
    result = find_ground_truth_text("002", ground_truth_map)
    assert result is None


def test_find_ground_truth_text_multiple_dots():
    """Test with multiple dots in name, base is before last dot."""
    ground_truth_map = {"file.tar": "text1"}
    result = find_ground_truth_text("file.tar.gz", ground_truth_map)
    assert result == "text1"

    # Lowercase
    result = find_ground_truth_text("FILE.TAR.GZ", ground_truth_map)
    assert result == "text1"


def test_find_ground_truth_text_empty_map():
    """Test with empty map and various names."""
    result = find_ground_truth_text("001.png", {})
    assert result is None

    result = find_ground_truth_text("", {})
    assert result is None
