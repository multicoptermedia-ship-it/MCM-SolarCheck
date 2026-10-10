"""Descriptor-based inspection of private publication directories on POSIX."""
from __future__ import annotations

import os
import stat


def open_private_directory_chain(root, customer_id, project_id):
    """Return an open project-directory fd; caller must close it.

    Root must be a trusted absolute path. Every component below root is opened
    relative to its parent with O_NOFOLLOW, so intermediate symlinks fail closed.
    """
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise NotImplementedError("secure directory descriptors require POSIX")
    from mcm_solarcheck.services.canonical_local_destination import _TOKEN
    for token in (customer_id, project_id):
        if not isinstance(token, str) or not _TOKEN.fullmatch(token):
            raise ValueError("invalid path token")
    root = os.fspath(root)
    if not os.path.isabs(root):
        raise ValueError("absolute trusted root required")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open(root, flags)
    try:
        for token in (customer_id, project_id):
            child = os.open(token, flags, dir_fd=parent)
            os.close(parent)
            parent = child
        if not stat.S_ISDIR(os.fstat(parent).st_mode):
            raise ValueError("not a directory")
        result = parent
        parent = -1
        return result
    finally:
        if parent >= 0:
            os.close(parent)
