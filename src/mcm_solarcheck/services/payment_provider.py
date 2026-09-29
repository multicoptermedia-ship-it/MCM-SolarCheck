"""Provider capability boundary independent of concrete payment vendors."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.payment_methods import PaymentMethod


@dataclass(frozen=True)
class PaymentProviderCapabilities:
    provider_id: str
    methods: frozenset[PaymentMethod]

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise ValueError("provider_id must be non-empty")
        object.__setattr__(self, "provider_id", self.provider_id.strip())
        if not self.methods:
            raise ValueError("provider must support at least one payment method")
        if not all(isinstance(method, PaymentMethod) for method in self.methods):
            raise ValueError("provider methods must be PaymentMethod values")

    def supports(self, method: PaymentMethod) -> bool:
        return method in self.methods

    def require(self, method: PaymentMethod) -> None:
        if not self.supports(method):
            raise ValueError(
                f"provider {self.provider_id} does not support {method.value}"
            )


class PaymentProviderRegistry:
    """Resolve provider capabilities without coupling product logic to vendors."""

    def __init__(self, providers: tuple[PaymentProviderCapabilities, ...]) -> None:
        if not providers:
            raise ValueError("at least one payment provider is required")
        by_id: dict[str, PaymentProviderCapabilities] = {}
        for provider in providers:
            if provider.provider_id in by_id:
                raise ValueError("duplicate payment provider_id")
            by_id[provider.provider_id] = provider
        self._providers = by_id

    def get(self, provider_id: str) -> PaymentProviderCapabilities:
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id must be non-empty")
        normalized = provider_id.strip()
        try:
            return self._providers[normalized]
        except KeyError:
            raise KeyError(provider_id) from None

    def supporting(self, method: PaymentMethod) -> tuple[PaymentProviderCapabilities, ...]:
        return tuple(
            provider
            for provider in self._providers.values()
            if provider.supports(method)
        )
