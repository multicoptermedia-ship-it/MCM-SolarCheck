"""Read-only SFTP directory inspection that distinguishes missing from failures."""
from __future__ import annotations

import errno
import stat

from mcm_solarcheck.infrastructure.ssh_exception_translation import translate_ssh_exception


class StrictReadOnlySFTPSession:
    def __init__(self, client):
        self.client = client

    def directory_exists(self, path):
        try:
            return stat.S_ISDIR(self.client.stat(path).st_mode)
        except OSError as exc:
            if exc.errno == errno.ENOENT:
                return False
            translated = translate_ssh_exception(exc)
            if translated is not exc:
                raise translated from exc
            raise

    def close(self):
        self.client.close()
