"""Reversible publication primitives shared by legacy and Registry extensions."""

from __future__ import annotations

import threading
import typing
from collections.abc import Callable
from dataclasses import dataclass

import fastapi
from app.business.info_base.resolver.main import Resolver, ResolverManager
from app.business.peer import PeerManager
from app.business.peer.contracts import PeerInbound
from app.business.source.main import SourceBase, SourceManager
from app.schemas.info_base.block import ResolverType
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
    """The observable side effects contributed by one Extension startup."""

    app: fastapi.FastAPI
    routes: tuple[typing.Any, ...]
    source_types_before: dict[str, type[SourceBase]]
    source_types_published: dict[str, type[SourceBase]]
    resolvers_before: dict[ResolverType, type[Resolver]]
    resolvers_published: dict[ResolverType, type[Resolver]]
    peer_inbounds_before: dict[CapabilityID, PeerInbound]
    peer_inbounds_published: dict[CapabilityID, PeerInbound]
    public_http_claim: PublicHTTPRouteClaim | None = None
    restored: bool = False

    def _contributed_source_types(self) -> dict[str, type[SourceBase]]:
        return {
            source_type: source_class
            for source_type, source_class in self.source_types_published.items()
            if self.source_types_before.get(source_type) is not source_class
        }

    def activate_source_types(self) -> None:
        """Persist only the source types published by this runtime."""
        contributed = self._contributed_source_types()
        if not contributed:
            return
        SourceManager.sync_source_types(contributed)

    def restore(self) -> None:
        """Withdraw this publication without disturbing unrelated later routes."""
        if self.restored:
            return

        route_ids = {id(route) for route in self.routes}
        self.app.router.routes[:] = [
            route for route in self.app.router.routes if id(route) not in route_ids
        ]
        PeerManager.restore_inbounds(
            self.peer_inbounds_before,
            self.peer_inbounds_published,
        )
        if self.public_http_claim is not None:
            self.public_http_claim.release()
            self.public_http_claim = None
        SourceManager.restore_source_types(
            self.source_types_before,
            self.source_types_published,
        )
        ResolverManager.restore_resolvers(
            self.resolvers_before,
            self.resolvers_published,
        )
        self.app.openapi_schema = None
        self.restored = True


@dataclass(frozen=True)
class ExtensionPublicationSnapshot:
    """Before-state used to finalize or roll back one startup publication."""

    app: fastapi.FastAPI
    route_ids: frozenset[int]
    source_types: dict[str, type[SourceBase]]
    resolvers: dict[ResolverType, type[Resolver]]
    peer_inbounds: dict[CapabilityID, PeerInbound]

    @classmethod
    def capture(cls, app: fastapi.FastAPI) -> ExtensionPublicationSnapshot:
        return cls(
            app=app,
            route_ids=frozenset(id(route) for route in app.router.routes),
            source_types=SourceManager.snapshot_source_types(),
            resolvers=ResolverManager.snapshot_resolvers(),
            peer_inbounds=PeerManager.snapshot_inbounds(),
        )

    def finish(self) -> ExtensionPublication:
        publication = ExtensionPublication(
            app=self.app,
            routes=tuple(
                route for route in self.app.router.routes if id(route) not in self.route_ids
            ),
            source_types_before=self.source_types,
            source_types_published=SourceManager.snapshot_source_types(),
            resolvers_before=self.resolvers,
            resolvers_published=ResolverManager.snapshot_resolvers(),
            peer_inbounds_before=self.peer_inbounds,
            peer_inbounds_published=PeerManager.snapshot_inbounds(),
        )
        self.app.openapi_schema = None
        return publication

    def rollback(self) -> None:
        self.finish().restore()
