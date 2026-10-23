from decimal import Decimal

import pytest

from mcm_solarcheck.services.project_creation import (
    CreateProjectRequest,
    ProjectCreationService,
)


def test_project_creation_stores_customer_upload_metadata() -> None:
    stored = []
    service = ProjectCreationService(stored.append)

    project = service.create(
        CreateProjectRequest(
            customer_id="user-1",
            project_id="P-1",
            name="Solarpark Nord",
            capacity_kwp=Decimal("850.5"),
        )
    )

    assert stored == [project]
    assert project.customer_id == "user-1"
    assert project.project_id == "P-1"
    assert project.name == "Solarpark Nord"
    assert project.capacity_kwp == Decimal("850.5")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("customer_id", " "),
        ("project_id", ""),
        ("name", " "),
        ("capacity_kwp", Decimal("0")),
        ("capacity_kwp", Decimal("-1")),
    ],
)
def test_project_creation_rejects_invalid_metadata(field, value) -> None:
    stored = []
    values = {
        "customer_id": "user-1",
        "project_id": "P-1",
        "name": "Solarpark Nord",
        "capacity_kwp": Decimal("850.5"),
    }
    values[field] = value
    service = ProjectCreationService(stored.append)

    with pytest.raises(ValueError):
        service.create(CreateProjectRequest(**values))

    assert stored == []


def test_automatic_project_creation_uses_verified_owner_not_email_or_client_id():
    collected = []

    def create_numbered(owner, anlage, capacity):
        collected.append((owner, anlage, capacity))
        return "sc-opaque-1", "SC-0001"

    service = ProjectCreationService(lambda _p: (_ for _ in ()).throw(
        AssertionError("legacy manual path must not be used")
    ), create_numbered=create_numbered)
    project = service.create_from_anlage(
        customer_id=" stable-user ", anlage=" Norddach ",
        capacity_kwp=Decimal("24.50"),
    )
    assert collected == [("stable-user", "Norddach", Decimal("24.50"))]
    assert project.project_id == "sc-opaque-1"
    assert project.display_number == "SC-0001"
    assert project.name == "Norddach"
