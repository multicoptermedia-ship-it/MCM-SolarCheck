import pytest

from mcm_solarcheck.infrastructure.ordered_ssh_client_factory import OrderedSSHClientFactory
from mcm_solarcheck.infrastructure.verified_read_only_sftp_connector import (
    VerifiedReadOnlySFTPConnector, _VerifiedSession,
)


def test_ordered_factory_preserves_original_error_when_close_fails():
    class Driver:
        def negotiate_without_authentication(self):
            raise ValueError("handshake failed")
        def close(self):
            raise OSError("close failed")

    with pytest.raises(ValueError, match="handshake failed"):
        OrderedSSHClientFactory(lambda config: Driver())(object())


def test_connector_preserves_verification_error_when_close_fails():
    class Client:
        def negotiated_host_key_blob(self):
            raise ValueError("bad server key")
        def close(self):
            raise OSError("close failed")

    with pytest.raises(ValueError, match="bad server key"):
        VerifiedReadOnlySFTPConnector(lambda config: Client()).open_verified_read_only(object())


def test_session_closes_both_resources_and_preserves_inspection_error():
    events = []
    class Resource:
        def __init__(self, label):
            self.label = label
        def close(self):
            events.append(self.label)
            raise OSError(self.label + " cleanup failed")

    with pytest.raises(ValueError, match="inspection failed"):
        with _VerifiedSession(Resource("client"), Resource("session")):
            raise ValueError("inspection failed")
    assert events == ["session", "client"]


def test_session_surfaces_cleanup_error_when_no_primary_error():
    class Resource:
        def close(self):
            raise OSError("cleanup failed")

    with pytest.raises(OSError, match="cleanup failed"):
        with _VerifiedSession(Resource(), Resource()):
            pass
