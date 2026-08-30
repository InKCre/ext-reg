"""Active effects published by one running Extension."""

from __future__ import annotations

import threading
import typing
from collections.abc import Callable
from dataclasses import dataclass

import fastapi
from app.business.peer import PeerManager
from app.business.source.main import SourceManager
from app.schemas.peer import CapabilityID


@dataclass(frozen=True)
class PublicHTTPRoute:
    """One exact Extension route intentionally published without Peer JWT."""

    method: typing.Literal["GET", "POST"]
    path: str

    def __post_init__(self) -> None:
        if (
            not self.path.startswith("/")
            or self.path == "/"
            or "{" in self.path
            or "}" in self.path
            or "*" in self.path
            or "?" in self.path
            or "#" in self.path
        ):
            raise ValueError("Public Extension route must be an exact relative path")


class PublicHTTPRouteClaim:
    """Process authority for exact public routes contributed by a runtime."""

    _lock = threading.Lock()
    _owners: typing.ClassVar[dict[tuple[str, str], object]] = {}

    def __init__(self, routes: frozenset[tuple[str, str]], token: object) -> None:
        self.routes = routes
        self._token = token
        self._released = False

    @classmethod
    def acquire(
        cls,
        extension_id: str,
        declarations: tuple[PublicHTTPRoute, ...],
        published_routes: tuple[typing.Any, ...],
    ) -> PublicHTTPRouteClaim | None:
        if not declarations:
            return None
        available = {
            (method, route.path)
            for route in published_routes
            for method in (getattr(route, "methods", None) or ())
            if isinstance(getattr(route, "path", None), str)
        }
        absolute = frozenset(
            (declaration.method, f"/{extension_id}{declaration.path}")
            for declaration in declarations
        )
        missing = absolute - available
        if missing:
            raise ValueError(f"Public Extension routes were not published: {sorted(missing)}")
        token = object()
        with cls._lock:
            conflicts = absolute & cls._owners.keys()
            if conflicts:
                raise ExtensionRuntimeClaimConflictError(
                    f"Public Extension route already claimed: {sorted(conflicts)}"
                )
            for route in absolute:
                cls._owners[route] = token
        return cls(absolute, token)

    @classmethod
    def permits(cls, method: str, path: str) -> bool:
        with cls._lock:
            return (method.upper(), path) in cls._owners

    def release(self) -> None:
        if self._released:
            return
        with self._lock:
            for route in self.routes:
                if self._owners.get(route) is self._token:
                    self._owners.pop(route)
            self._released = True


class ExtensionRuntimeClaimConflictError(RuntimeError):
    """Raised when another manager already owns an Extension runtime ID."""


class ExtensionRuntimeClaim:
    """An atomic, process-local claim for one canonical Extension runtime ID."""

    _lock = threading.Lock()
    _owners: typing.ClassVar[dict[str, object]] = {}

    def __init__(self, extension_id: str, token: object) -> None:
        self.extension_id = extension_id
        self._token = token
        self._released = False

    @classmethod
    def acquire(cls, extension_id: str) -> ExtensionRuntimeClaim:
        token = object()
        with cls._lock:
            if extension_id in cls._owners:
                raise ExtensionRuntimeClaimConflictError(
                    f"Extension runtime {extension_id} already owns the canonical module"
                )
            cls._owners[extension_id] = token
        return cls(extension_id, token)

    def release(self) -> None:
        """Release this exact claim; repeated cleanup is intentionally harmless."""
        if self._released:
            return
        with self._lock:
            if self._owners.get(self.extension_id) is self._token:
                self._owners.pop(self.extension_id)
            self._released = True


@dataclass(frozen=True)
class ExtensionRuntimeRecord:
    """The narrow deployment state an Extension class needs at runtime."""

    extension_id: str
    config: dict[str, typing.Any]
    read_config: Callable[[], dict[str, typing.Any]]
    persist_config: Callable[[dict[str, typing.Any]], None]
    read_state: Callable[[], dict[str, typing.Any]]
    mutate_state: Callable[
        [Callable[[dict[str, typing.Any]], dict[str, typing.Any]]],
        dict[str, typing.Any],
    ]
    mutate_config_and_state: Callable[
        [
            Callable[
                [dict[str, typing.Any], dict[str, typing.Any]],
                tuple[dict[str, typing.Any], dict[str, typing.Any]],
            ]
        ],
        tuple[dict[str, typing.Any], dict[str, typing.Any]],
    ]
    persist_config_schema: Callable[[dict[str, typing.Any]], None]


@dataclass
class ExtensionPublication:
    """The reversible effects contributed by one Extension startup.

    Imported Source and Resolver types are deliberately absent: Python type
    registration is process-monotonic, while routes and Peer inbounds are
    active effects owned by one running instance.
    """

    app: fastapi.FastAPI
    routes: tuple[typing.Any, ...] = ()
    peer_inbounds: tuple[CapabilityID, ...] = ()
    public_http_claim: PublicHTTPRouteClaim | None = None
    active: bool = True

    def activate_source_types(self) -> None:
        """Synchronize the process-monotonic Source catalog."""
        SourceManager.sync_source_types()

    def withdraw(self) -> None:
        """Withdraw this instance's exact active effects."""
        if not self.active:
            return

        route_ids = {id(route) for route in self.routes}
        self.app.router.routes[:] = [
            route for route in self.app.router.routes if id(route) not in route_ids
        ]
        for capability in self.peer_inbounds:
            PeerManager.unregister_inbound(capability)
        if self.public_http_claim is not None:
            self.public_http_claim.release()
            self.public_http_claim = None
        self.app.openapi_schema = None
        self.active = False
