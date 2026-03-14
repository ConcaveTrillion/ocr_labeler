def test_get_saved_projects_root_linux_uses_xdg_data_home(monkeypatch, tmp_path):
    from ocr_labeler.operations.persistence import persistence_paths_operations
    from ocr_labeler.operations.persistence.persistence_paths_operations import (
        PersistencePathsOperations,
    )

    xdg_data_home = tmp_path / "xdg-data"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data_home))
    monkeypatch.setattr(
        persistence_paths_operations.platform,
        "system",
        lambda: "Linux",
    )

    root = PersistencePathsOperations.get_saved_projects_root()

    assert root == xdg_data_home / "pgdp-ocr-labeler" / "labeled-projects"


def test_get_project_backups_root_linux_uses_xdg_data_home(monkeypatch, tmp_path):
    from ocr_labeler.operations.persistence import persistence_paths_operations
    from ocr_labeler.operations.persistence.persistence_paths_operations import (
        PersistencePathsOperations,
    )

    xdg_data_home = tmp_path / "xdg-data"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data_home))
    monkeypatch.setattr(
        persistence_paths_operations.platform,
        "system",
        lambda: "Linux",
    )

    root = PersistencePathsOperations.get_project_backups_root()

    assert root == xdg_data_home / "pgdp-ocr-labeler" / "project-backups"
