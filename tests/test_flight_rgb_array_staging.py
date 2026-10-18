"""Read-only staging diagnostics must not delete or repair artifacts."""
import pytest

from mcm_solarcheck.services.flight_rgb_array_staging import inspect_rgb_array_staging


def test_reports_staging_without_changing_files(tmp_path):
    leftover = tmp_path / ".rgb-array-abc.tmp"
    leftover.write_bytes(b"partial customer derived data")
    (tmp_path / "working.npy").write_bytes(b"other data")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = inspect_rgb_array_staging(tmp_path)
    assert result == {
        "staging_files": [{"name": ".rgb-array-abc.tmp",
                           "size_bytes": len(before[leftover.name])}],
        "requires_manual_review": True,
        "read_only": True,
    }
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_empty_staging_directory_needs_no_review(tmp_path):
    assert inspect_rgb_array_staging(tmp_path)["requires_manual_review"] is False


def test_rejects_symlink(tmp_path):
    target = tmp_path / "source"
    target.write_bytes(b"test")
    link = tmp_path / ".rgb-array-linked.tmp"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError, match="symlink"):
        inspect_rgb_array_staging(tmp_path)
