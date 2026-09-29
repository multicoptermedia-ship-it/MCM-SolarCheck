"""Route secret references to scheme-specific runtime resolvers."""

from __future__ import annotations

from collections.abc import Mapping

from mcm_solarcheck.services.secret_resolver import SecretResolver


class SecretResolverRouter:
    def __init__(self, resolvers: Mapping[str, SecretResolver]) -> None:
        if not resolvers:
            raise ValueError("at least one secret resolver is required")
        normalized: dict[str, SecretResolver] = {}
        for scheme, resolver in resolvers.items():
            if not isinstance(scheme, str) or not scheme.strip():
                raise ValueError("secret resolver scheme must be non-empty")
            key = scheme.strip().removesuffix(":")
            if not key:
                raise ValueError("secret resolver scheme must be non-empty")
            if key in normalized:
                raise ValueError("duplicate secret resolver scheme")
            normalized[key] = resolver
        self._resolvers = normalized

    def resolve(self, reference: str) -> str:
        if not isinstance(reference, str) or ":" not in reference:
            raise ValueError("secret reference must include a scheme")
        scheme = reference.split(":", 1)[0].strip()
        if not scheme:
            raise ValueError("secret reference must include a scheme")
        try:
            resolver = self._resolvers[scheme]
        except KeyError:
            raise ValueError(f"unsupported secret reference scheme: {scheme}") from None
        return resolver.resolve(reference)
