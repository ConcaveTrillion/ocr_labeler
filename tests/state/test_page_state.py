from ocr_labeler.state.page_state import PageState


def test_project_state_change_refreshes_loading_cache_when_page_finishes_loading(
    tmp_path,
):
    """Ensure Loading... placeholders are replaced after async load completion."""
    page_state = PageState()

    class ParentStateStub:
        def __init__(self):
            self.current_page_index = 0
            self.on_change = []
            self._project = None

        def ensure_page(self, index: int, force_ocr: bool = False):
            _ = force_ocr
            return self._project.pages[index]

    class ProjectStub:
        def __init__(self):
            self.pages = [None, None]
            self.ground_truth_map = {"page_002.png": "ground truth text"}

    class LoadedPageStub:
        def __init__(self, text: str, name: str):
            self.text = text
            self.name = name

    parent_state = ParentStateStub()
    project = ProjectStub()
    parent_state._project = project

    page_state.set_project_context(project, tmp_path, parent_state)
    on_change_callback = parent_state.on_change[0]

    parent_state.current_page_index = 1
    on_change_callback()
    assert page_state.current_ocr_text == "Loading..."
    assert page_state.current_gt_text == "Loading..."

    project.pages[1] = LoadedPageStub(text="ocr text", name="page_002.png")
    on_change_callback()

    assert page_state.current_ocr_text == "ocr text"
    assert page_state.current_gt_text == "ground truth text"
