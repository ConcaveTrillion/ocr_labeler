from __future__ import annotations

from ocr_labeler.state import AppState
from ocr_labeler.views.image_tabs import ImageTabs
from ocr_labeler.views.text_tabs import TextTabs


def test_ui_uses_project_state():
    """Test that UI components correctly access project state."""
    # Create an app state
    state = AppState()

    # Verify that we can access project state
    assert state.project_state is not None
    assert hasattr(state.project_state, "project")
    assert hasattr(state.project_state, "current_page_native")
    assert hasattr(state.project_state, "is_loading")

    # Test that navigation methods are properly delegated
    state.project_state.next_page()  # Should not crash
    state.project_state.prev_page()  # Should not crash
    state.project_state.goto_page_number(1)  # Should not crash


def test_view_components_work_with_project_state():
    """Test that view components can work with the project state structure."""
    state = AppState()

    # Test ImageTabs
    image_tabs = ImageTabs()
    # This should not crash even with no project loaded
    image_tabs.update_images(state)

    # Test TextTabs
    text_tabs = TextTabs()
    # This should not crash even with no project loaded
    text_tabs.update_text(state)


def test_project_state_direct_access_and_delegation_removal():
    """Test direct access to project state and that delegation methods are removed."""
    state = AppState()

    # These should work through direct project_state access
    assert state.project_state.project is not None
    assert state.project_state.project_root == state.project_state.project_root
    # current_page_native should now be accessed directly from project_state
    assert hasattr(state.project_state, "current_page_native")

    # Test setters work
    state.is_loading = True
    assert state.project_state.is_loading is True
    assert (
        state.is_loading is True
    )  # Should be True because project_state.is_loading is True

    state.is_loading = False
    assert state.project_state.is_loading is False

    # Test that delegation methods and compatibility properties are no longer available
    assert not hasattr(state, "next_page")
    assert not hasattr(state, "prev_page")
    assert not hasattr(state, "goto_page_number")
    assert not hasattr(state, "current_page")
    assert not hasattr(state, "reload_ground_truth")
    assert not hasattr(state, "current_page_native")  # Should no longer be on AppState
    assert not hasattr(state, "project")  # Should no longer be on AppState
    assert not hasattr(state, "project_root")  # Should no longer be on AppState
