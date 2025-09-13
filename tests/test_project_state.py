from __future__ import annotations

from ocr_labeler.state.project_state import ProjectState


def test_project_state_initialization():
    """Test that ProjectState initializes correctly."""
    state = ProjectState()
    assert state.project is not None
    assert state.current_page_native is None
    assert state.is_loading is False
    assert state.on_change is None


def test_project_state_notification():
    """Test that ProjectState notification system works."""
    state = ProjectState()
    calls = []
    state.on_change = lambda: calls.append("notified")
    state.notify()
    assert calls == ["notified"]


def test_project_state_delegation():
    """Test that ProjectState methods delegate correctly."""
    state = ProjectState()

    # Test navigation methods exist and can be called
    # (These won't do much without a loaded project, but they shouldn't crash)
    state.next_page()
    state.prev_page()
    state.goto_page_number(1)

    # Test current page returns None when no project loaded
    assert state.current_page() is None
