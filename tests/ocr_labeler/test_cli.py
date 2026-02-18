from __future__ import annotations

from types import SimpleNamespace

import pytest

import ocr_labeler.cli as cli


def test_parse_args_verbose_counts():
    assert cli.parse_args([]).verbose == 0
    assert cli.parse_args(["-v"]).verbose == 1
    assert cli.parse_args(["-vv"]).verbose == 2
    assert cli.parse_args(["-vvv"]).verbose == 3


def test_parse_args_page_timing_flag():
    assert cli.parse_args([]).page_timing is False
    assert cli.parse_args(["--page-timing"]).page_timing is True


def test_parse_args_rejects_removed_log_file_flag():
    with pytest.raises(SystemExit):
        cli.parse_args(["--log-file", "app.log"])


@pytest.mark.parametrize(
    (
        "verbose",
        "expected_app",
        "expected_important_dep",
        "expected_dep",
        "expected_root",
    ),
    [
        (0, "INFO", "WARNING", "WARNING", "WARNING"),
        (1, "DEBUG", "WARNING", "WARNING", "WARNING"),
        (2, "DEBUG", "DEBUG", "WARNING", "WARNING"),
        (3, "DEBUG", "DEBUG", "DEBUG", "DEBUG"),
    ],
)
def test_get_logging_configuration_levels(
    verbose: int,
    expected_app: str,
    expected_important_dep: str,
    expected_dep: str,
    expected_root: str,
):
    cfg = cli.get_logging_configuration(verbose=verbose)

    assert cfg["root"]["handlers"] == ["null"]
    assert cfg["loggers"]["ocr_labeler"]["handlers"] == ["null"]
    assert cfg["root"]["level"] == expected_root
    assert cfg["loggers"]["ocr_labeler"]["level"] == expected_app
    assert cfg["loggers"]["pd_book_tools"]["level"] == expected_important_dep

    for dep_name in [
        "nicegui",
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "engineio",
        "socketio",
        "urllib3",
    ]:
        assert cfg["loggers"][dep_name]["level"] == expected_dep


def test_get_logging_configuration_enables_page_timing_logger():
    cfg = cli.get_logging_configuration(verbose=0, page_timing=True)

    assert "page_timing_console" in cfg["handlers"]
    assert cfg["loggers"]["ocr_labeler.page_timing"]["level"] == "INFO"
    assert cfg["loggers"]["ocr_labeler.page_timing"]["handlers"] == [
        "page_timing_console"
    ]
    assert cfg["loggers"]["ocr_labeler.page_timing"]["propagate"] is False


@pytest.mark.parametrize(
    ("verbose", "expected_uvicorn_level"),
    [
        (0, "warning"),
        (1, "warning"),
        (2, "warning"),
        (3, "debug"),
    ],
)
def test_main_sets_uvicorn_level_from_verbosity(
    monkeypatch: pytest.MonkeyPatch,
    verbose: int,
    expected_uvicorn_level: str,
):
    class DummyApp:
        def __init__(self, **kwargs):
            self.init_kwargs = kwargs
            self.run_kwargs = None

        def run(self, **kwargs):
            self.run_kwargs = kwargs

    captured = {"cfg": None, "app": None}

    def fake_parse_args(_argv):
        return SimpleNamespace(
            project_dir=".",
            projects_root=None,
            host="127.0.0.1",
            port=8080,
            font_name="monospace",
            font_path=None,
            debugpy=False,
            verbose=verbose,
            page_timing=False,
        )

    def fake_dict_config(cfg):
        captured["cfg"] = cfg

    def fake_app_factory(**kwargs):
        app = DummyApp(**kwargs)
        captured["app"] = app
        return app

    monkeypatch.setattr(cli, "parse_args", fake_parse_args)
    monkeypatch.setattr(cli.logging.config, "dictConfig", fake_dict_config)
    monkeypatch.setattr(cli, "NiceGuiLabeler", fake_app_factory)

    cli.main([])

    assert captured["cfg"] is not None
    assert captured["app"] is not None
    assert captured["app"].run_kwargs is not None
    assert captured["app"].run_kwargs["uvicorn_logging_level"] == expected_uvicorn_level
