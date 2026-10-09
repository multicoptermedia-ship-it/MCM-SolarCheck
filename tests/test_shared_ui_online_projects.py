"""Online project projection must be customer scoped."""
from types import SimpleNamespace
import pytest

from shared_ui.online_projects import online_project_list


class CustomerProjects:
    def projects_for_customer(self, customer_id):
        assert customer_id == "alice"
        return (SimpleNamespace(project_id="p1", name="Nord"),)

    def projects(self):
        raise AssertionError("unscoped project listing must not be called")


def test_customer_scoped_listing():
    assert online_project_list(CustomerProjects(), " alice ") == [{"id": "p1", "name": "Nord"}]


def test_missing_customer_rejected():
    with pytest.raises(PermissionError):
        online_project_list(CustomerProjects(), " ")
