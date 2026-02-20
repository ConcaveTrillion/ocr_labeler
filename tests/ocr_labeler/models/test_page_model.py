from __future__ import annotations

from pd_book_tools.ocr.page import Page

from ocr_labeler.models.page_model import PageModel


def test_page_model_defaults_from_page_attributes(tmp_path):
    page = Page(width=100, height=100, page_index=0, items=[])
    page.image_path = str(tmp_path / "001.png")  # type: ignore[attr-defined]
    page.name = "001.png"  # type: ignore[attr-defined]
    page.index = 0  # type: ignore[attr-defined]

    model = PageModel(page=page, page_source="ocr")

    assert model.page is page
    assert model.page_source == "ocr"
    assert model.image_path == str(tmp_path / "001.png")
    assert model.name == "001.png"
    assert model.index == 0


def test_page_model_delegates_unknown_attributes_to_page():
    page = Page(width=100, height=100, page_index=0, items=[])
    page.custom_attr = "value"  # type: ignore[attr-defined]

    model = PageModel(page=page)

    assert model.custom_attr == "value"


def test_page_model_live_sync_with_wrapped_page(tmp_path):
    page = Page(width=100, height=100, page_index=0, items=[])
    page.image_path = str(tmp_path / "001.png")  # type: ignore[attr-defined]
    page.name = "001.png"  # type: ignore[attr-defined]
    page.index = 0  # type: ignore[attr-defined]

    model = PageModel(page=page)

    page.image_path = str(tmp_path / "002.png")  # type: ignore[attr-defined]
    page.name = "002.png"  # type: ignore[attr-defined]
    page.index = 1  # type: ignore[attr-defined]

    assert model.image_path == str(tmp_path / "002.png")
    assert model.name == "002.png"
    assert model.index == 1

    model.image_path = str(tmp_path / "003.png")
    model.name = "003.png"
    model.index = 2

    assert page.image_path == str(tmp_path / "003.png")  # type: ignore[attr-defined]
    assert page.name == "003.png"  # type: ignore[attr-defined]
    assert page.index == 2  # type: ignore[attr-defined]


def test_page_model_live_sync_with_wrapped_page_ocr_provenance():
    page = Page(width=100, height=100, page_index=0, items=[])
    page.ocr_provenance = {"engine": "doctr", "version": "0.0.1"}  # type: ignore[attr-defined]

    model = PageModel(page=page)

    assert model.ocr_provenance == {"engine": "doctr", "version": "0.0.1"}

    page.ocr_provenance = {"engine": "doctr", "version": "0.0.2"}  # type: ignore[attr-defined]
    assert model.ocr_provenance == {"engine": "doctr", "version": "0.0.2"}

    model.ocr_provenance = {"engine": "doctr", "version": "0.0.3"}
    assert page.ocr_provenance == {"engine": "doctr", "version": "0.0.3"}  # type: ignore[attr-defined]
