import os

import pytest

from mcm_solarcheck.infrastructure.private_directory_descriptors import open_private_directory_chain


@pytest.mark.skipif(os.name != "posix", reason="POSIX descriptor semantics required")
def test_open_private_project_directory_without_following_symlinks(tmp_path):
    root = tmp_path / "storage"
    project = root / "customer" / "project"
    project.mkdir(parents=True)
    fd = open_private_directory_chain(root, "customer", "project")
    try:
        assert os.fstat(fd).st_ino == project.stat().st_ino
    finally:
        os.close(fd)


@pytest.mark.skipif(os.name != "posix", reason="POSIX descriptor semantics required")
def test_intermediate_symlink_rejected(tmp_path):
    root = tmp_path / "storage"
    root.mkdir()
    outside = tmp_path / "outside"
    (outside / "project").mkdir(parents=True)
    (root / "customer").symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError):
        open_private_directory_chain(root, "customer", "project")


@pytest.mark.skipif(os.name != "posix", reason="POSIX descriptor semantics required")
def test_project_symlink_rejected(tmp_path):
    root = tmp_path / "storage"
    (root / "customer").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "customer" / "project").symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError):
        open_private_directory_chain(root, "customer", "project")
