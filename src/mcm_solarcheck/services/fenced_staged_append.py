"""Opt-in fenced append interface; the remote must enforce generations atomically.

A local preflight generation check is NOT a substitute for backend enforcement.
"""
from __future__ import annotations


class FencedAppendUnsupported(RuntimeError):
    pass


class FencedStagedAppender:
    def __init__(self, remote):
        self.remote = remote

    def append(self, staging_key: str, *, generation: int, expected_offset: int, chunks):
        if type(generation) is not int or generation <= 0:
            raise ValueError("invalid fencing generation")
        if type(expected_offset) is not int or expected_offset < 0:
            raise ValueError("invalid offset")
        operation = getattr(self.remote, "append_chunks_if_generation_and_size", None)
        if not callable(operation):
            raise FencedAppendUnsupported(
                "backend must atomically validate generation and expected offset"
            )
        return operation(staging_key, generation, expected_offset, chunks)
