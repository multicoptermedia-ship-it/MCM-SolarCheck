"""Explicitly ordered SSH session factory with an injected handshake driver.

A driver must negotiate SSH without authenticating, expose the negotiated
server key, and authenticate only when called by this factory.
"""
from __future__ import annotations

from mcm_solarcheck.infrastructure.strict_ssh_host_key_policy import StrictHostKeyPolicy


class OrderedSSHClientFactory:
    def __init__(self, driver_factory):
        self.driver_factory = driver_factory

    def __call__(self, config):
        driver = self.driver_factory(config)
        try:
            driver.negotiate_without_authentication()
            policy = StrictHostKeyPolicy(config.host_key_sha256)
            policy.check(driver.negotiated_host_key_blob())
            policy.require_verified()
            driver.authenticate()
            return _AuthenticatedClient(driver)
        except BaseException:
            try:
                driver.close()
            except Exception:
                pass
            raise


class _AuthenticatedClient:
    def __init__(self, driver):
        self.driver = driver

    def negotiated_host_key_blob(self):
        return self.driver.negotiated_host_key_blob()

    def open_read_only_sftp(self):
        return self.driver.open_read_only_sftp()

    def close(self):
        self.driver.close()
