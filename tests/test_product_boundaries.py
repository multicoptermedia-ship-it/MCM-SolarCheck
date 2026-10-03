from __future__ import annotations

import pytest

from mcm_solarcheck.offline import OfflineProduct
from mcm_solarcheck.online import OnlineProduct


class Production:
    def __init__(self, active: bool) -> None:
        self.active = active

    def require_active(self) -> None:
        if not self.active:
            raise RuntimeError("production inactive")


class Services:
    def __init__(self, active: bool) -> None:
        self.production = Production(active)


def test_online_product_is_physically_separate_and_requires_active_production() -> None:
    product = OnlineProduct.compose(Services(False))

    with pytest.raises(RuntimeError, match="production inactive"):
        product.require_customer_entry()


def test_online_product_allows_entry_after_activation() -> None:
    OnlineProduct.compose(Services(True)).require_customer_entry()


def test_offline_product_is_physically_separate_and_needs_no_online_state() -> None:
    OfflineProduct().require_customer_entry()


def test_online_and_offline_products_have_distinct_module_boundaries() -> None:
    assert OnlineProduct.__module__.startswith("mcm_solarcheck.online.")
    assert OfflineProduct.__module__.startswith("mcm_solarcheck.offline.")
