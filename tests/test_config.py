from pathlib import Path

from archlens.infra.config import AppConfig, load_config


def test_load_config_reads_protected_packages_and_cache_policy(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        '[protected]\npackages = ["my-tool", "linux-lts"]\n\n[cache]\nkeep_versions = 4\n',
        encoding="utf-8",
    )
    assert load_config(path) == AppConfig(frozenset({"my-tool", "linux-lts"}), 4)


def test_invalid_config_falls_back_to_safe_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("not valid = [", encoding="utf-8")
    assert load_config(path) == AppConfig()
