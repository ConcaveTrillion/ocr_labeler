def test_get_default_state_root_linux_uses_xdg_data_home(monkeypatch, tmp_path):
    from ocr_labeler.operations.persistence import persistence_paths_operations
    from ocr_labeler.operations.persistence.state_persistence_operations import (
        StatePersistenceOperations,
    )

    xdg_data_home = tmp_path / "xdg-data"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data_home))
    monkeypatch.setattr(
        persistence_paths_operations.platform,
        "system",
        lambda: "Linux",
    )

    root = StatePersistenceOperations.get_default_state_root()

    assert root == xdg_data_home / "pgdp-ocr-labeler" / "state"


def test_get_default_state_file_path_uses_state_root(monkeypatch, tmp_path):
    from ocr_labeler.operations.persistence import persistence_paths_operations
    from ocr_labeler.operations.persistence.state_persistence_operations import (
        StatePersistenceOperations,
    )

    xdg_data_home = tmp_path / "xdg-data"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data_home))
    monkeypatch.setattr(
        persistence_paths_operations.platform,
        "system",
        lambda: "Linux",
    )

    path = StatePersistenceOperations.get_default_state_file_path("app_state")

    assert path == (xdg_data_home / "pgdp-ocr-labeler" / "state" / "app_state.json")
