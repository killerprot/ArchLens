from pathlib import Path

from archlens.core.cache_analysis import parse_cache_filename, scan_cache


def test_parse_cache_filename(tmp_path: Path) -> None:
    package = tmp_path / "python-pyside6-6.8.1-1-x86_64.pkg.tar.zst"
    package.write_bytes(b"1234")
    parsed = parse_cache_filename(package)
    assert parsed is not None
    assert parsed.name == "python-pyside6"
    assert parsed.version == "6.8.1-1"
    assert parsed.size == 4


def test_scan_cache_ignores_unknown_files(tmp_path: Path) -> None:
    (tmp_path / "not-a-package.txt").write_text("x")
    package = tmp_path / "demo-1.0-1-x86_64.pkg.tar.zst"
    package.write_bytes(b"123")
    assert len(scan_cache(tmp_path)) == 1
