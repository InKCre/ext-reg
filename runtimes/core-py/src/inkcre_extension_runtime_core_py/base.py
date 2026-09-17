"""Extension-facing lifecycle bound directly to Core's rich model."""

from __future__ import annotations

import typing
from collections.abc import Iterator
from contextlib import contextmanager

import pydantic

from .errors import ExtensionLifecycleError, translate_host_model_error

if typing.TYPE_CHECKING:
    from .publication import ExtensionPublication


class EmptyConfig(pydantic.BaseModel): ...


class EmptyState(pydantic.BaseModel): ...


class ExtensionBase[ConfigT: pydantic.BaseModel, StateT: pydantic.BaseModel]:
    """One Extension code type bound to its current Core Active Record."""

    def __init_subclass__(
        cls,
        ext_id: str,
        config_cls: type[ConfigT] = EmptyConfig,
        state_cls: type[StateT] = EmptyState,
        **kwargs: typing.Any,
    ) -> None:
        super().__init_subclass__(**kwargs)
        cls.__extid__ = ext_id
        cls.__configcls__ = config_cls
        cls.__statecls__ = state_cls
        cls.__configschema__ = config_cls.model_json_schema()

    @classmethod
    def bind(cls, model: typing.Any) -> None:
        if cls.__dict__.get("__model__") is not None:
            raise ExtensionLifecycleError(f"Extension {cls.__extid__} is already bound")
        local_id = model.name.partition("/")[2]
        if not local_id or local_id != cls.__extid__:
            raise ExtensionLifecycleError("Extension class identity differs from installed model")
        cls.__model__ = model

    @classmethod
    def unbind(cls) -> None:
        if "__model__" in cls.__dict__:
            del cls.__model__

    @classmethod
    def _model(cls) -> typing.Any:
        model = cls.__dict__.get("__model__")
        if model is None:
            raise ExtensionLifecycleError(f"Extension {cls.__extid__} is not bound")
        return model

    @classmethod
    def get_config(cls) -> ConfigT:
        return cls.__configcls__.model_validate(cls._model().config)

    @classmethod
    def update_config(cls, value: dict[str, typing.Any] | ConfigT) -> ConfigT:
        config = (
            value
            if isinstance(value, cls.__configcls__)
            else cls.__configcls__.model_validate(value)
        )
        try:
            cls.__model__ = cls._model().update_config(config.model_dump(mode="json"))
        except Exception as error:
            translate_host_model_error(error)
        return config

    @classmethod
    def get_state(cls) -> StateT:
        try:
            state = cls._model().read_state()
        except Exception as error:
            translate_host_model_error(error)
        return cls.__statecls__.model_validate(state)

    @classmethod
    def mutate_state(cls, transform: typing.Callable[[StateT], StateT]) -> StateT:
        result: StateT | None = None

        def mutate(raw: dict[str, typing.Any]) -> dict[str, typing.Any]:
            nonlocal result
            updated = transform(cls.__statecls__.model_validate(raw))
            if not isinstance(updated, cls.__statecls__):
                raise TypeError("Extension state transform returned the wrong model")
            result = updated
            return updated.model_dump(mode="json")

        try:
            cls._model().mutate_state(mutate)
        except Exception as error:
            translate_host_model_error(error)
        # The Host invokes the transform under its transaction and commits its
        # returned JSON unchanged. Keep the typed result rather than revalidating it.
        return typing.cast(StateT, result)

    @classmethod
    def mutate_config_and_state(
        cls, transform: typing.Callable[[ConfigT, StateT], tuple[ConfigT, StateT]]
    ) -> tuple[ConfigT, StateT]:
        result: tuple[ConfigT, StateT] | None = None

        def mutate(
            config: dict[str, typing.Any], state: dict[str, typing.Any]
        ) -> tuple[dict[str, typing.Any], dict[str, typing.Any]]:
            nonlocal result
            new_config, new_state = transform(
                cls.__configcls__.model_validate(config), cls.__statecls__.model_validate(state)
            )
            if not isinstance(new_config, cls.__configcls__) or not isinstance(
                new_state, cls.__statecls__
            ):
                raise TypeError("Extension config/state transform returned the wrong models")
            result = new_config, new_state
            return new_config.model_dump(mode="json"), new_state.model_dump(mode="json")

        try:
            cls._model().mutate_config_and_state(mutate)
        except Exception as error:
            translate_host_model_error(error)
        return typing.cast(tuple[ConfigT, StateT], result)

    @classmethod
    async def update_config_async(cls, value: dict[str, typing.Any] | ConfigT) -> ConfigT:
        """Persist validated configuration through the Host async capability."""
        config = (
            value
            if isinstance(value, cls.__configcls__)
            else cls.__configcls__.model_validate(value)
        )
        try:
            cls.__model__ = await cls._model().update_config_async(config.model_dump(mode="json"))
        except Exception as error:
            translate_host_model_error(error)
        return config

    @classmethod
    async def get_state_async(cls) -> StateT:
        """Read fresh state through the Host async capability."""
        try:
            state = await cls._model().read_state_async()
        except Exception as error:
            translate_host_model_error(error)
        return cls.__statecls__.model_validate(state)

    @classmethod
    async def mutate_state_async(cls, transform: typing.Callable[[StateT], StateT]) -> StateT:
        """Await one committed state mutation; transform runs synchronously under the Host lock."""
        result: StateT | None = None

        def mutate(raw: dict[str, typing.Any]) -> dict[str, typing.Any]:
            nonlocal result
            updated = transform(cls.__statecls__.model_validate(raw))
            if not isinstance(updated, cls.__statecls__):
                raise TypeError("Extension state transform returned the wrong model")
            result = updated
            return updated.model_dump(mode="json")

        try:
            await cls._model().mutate_state_async(mutate)
        except Exception as error:
            translate_host_model_error(error)
        # The Host invokes the transform under its transaction and commits its
        # returned JSON unchanged. Keep the typed result rather than revalidating it.
        return typing.cast(StateT, result)

    @classmethod
    async def mutate_config_and_state_async(
        cls, transform: typing.Callable[[ConfigT, StateT], tuple[ConfigT, StateT]]
    ) -> tuple[ConfigT, StateT]:
        """Await one atomic config/state mutation with a synchronous typed transform."""
        result: tuple[ConfigT, StateT] | None = None

        def mutate(
            config: dict[str, typing.Any], state: dict[str, typing.Any]
        ) -> tuple[dict[str, typing.Any], dict[str, typing.Any]]:
            nonlocal result
            new_config, new_state = transform(
                cls.__configcls__.model_validate(config), cls.__statecls__.model_validate(state)
            )
            if not isinstance(new_config, cls.__configcls__) or not isinstance(
                new_state, cls.__statecls__
            ):
                raise TypeError("Extension config/state transform returned the wrong models")
            result = new_config, new_state
            return new_config.model_dump(mode="json"), new_state.model_dump(mode="json")

        try:
            await cls._model().mutate_config_and_state_async(mutate)
        except Exception as error:
            translate_host_model_error(error)
        return typing.cast(tuple[ConfigT, StateT], result)

    @classmethod
    def on_start(cls, app: typing.Any) -> None:
        """Publish contributions using the synchronous Host persistence contract."""
        with cls._publication_scope(app) as publication:
            publication.activate_source_types()
            try:
                cls.__model__ = cls._model().update_config_schema(dict(cls.__configschema__))
            except Exception as error:
                translate_host_model_error(error)

    @classmethod
    async def on_start_async(cls, app: typing.Any) -> None:
        """Publish contributions and await catalog/schema persistence before becoming active."""
        with cls._publication_scope(app) as publication:
            await publication.activate_source_types_async()
            try:
                cls.__model__ = await cls._model().update_config_schema_async(
                    dict(cls.__configschema__)
                )
            except Exception as error:
                translate_host_model_error(error)

    @classmethod
    @contextmanager
    def _publication_scope(cls, app: typing.Any) -> Iterator[ExtensionPublication]:
        import fastapi
        from app.business.peer import PeerManager

        from .publication import (
            ExtensionPublication,
            PublicHTTPRouteClaim,
        )

        if cls.runtime_active() or cls.__dict__.get("__runtime_starting__", False):
            raise ExtensionLifecycleError(
                f"Extension {cls.__extid__} is already active or starting"
            )
        publication = ExtensionPublication(app)
        cls.__runtime_starting__ = True
        try:
            router = fastapi.APIRouter(
                prefix=f"/{cls.__extid__}", dependencies=cls.api_dependencies()
            )
            cls._register_apis(router)
            route_start = len(app.router.routes)
            app.include_router(router, tags=["extension", cls.__extid__])
            publication.routes = tuple(app.router.routes[route_start:])
            cls._init_sources()
            cls._init_resolvers()
            inbounds = cls.peer_inbounds()
            for inbound in inbounds:
                if PeerManager.register_inbound(inbound):
                    publication.peer_inbounds += (inbound.capability,)
            publication.public_http_claim = PublicHTTPRouteClaim.acquire(
                cls.__extid__, cls.public_http_routes(), publication.routes
            )
            yield publication
        except BaseException:
            # Cancellation during Host persistence must revoke already-published effects.
            publication.withdraw()
            raise
        else:
            cls.__runtime_publication__ = publication
        finally:
            del cls.__runtime_starting__

    @classmethod
    def api_dependencies(cls) -> list[typing.Any]:
        from app.middleware import require_peer_jwt
        from fastapi import Depends

        return [Depends(require_peer_jwt)]

    @classmethod
    def peer_inbounds(cls) -> tuple[typing.Any, ...]:
        return ()

    @classmethod
    def public_http_routes(cls) -> tuple[typing.Any, ...]:
        return ()

    @classmethod
    def _register_apis(cls, router: typing.Any) -> None:
        """Register Extension-owned API endpoints."""

    @classmethod
    def _init_sources(cls) -> None: ...

    @classmethod
    def _init_resolvers(cls) -> None: ...

    @classmethod
    def load_decoders(cls) -> None:
        cls._init_resolvers()

    @classmethod
    def runtime_active(cls) -> bool:
        publication = cls.__dict__.get("__runtime_publication__")
        return publication is not None and publication.active

    @classmethod
    def unpublish(cls) -> None:
        publication = cls.__dict__.get("__runtime_publication__")
        if publication is not None:
            publication.withdraw()

    @classmethod
    def release_runtime(cls) -> None:
        if "__runtime_publication__" in cls.__dict__:
            del cls.__runtime_publication__

    @classmethod
    async def on_close(cls) -> None:
        """Withdraw resources owned outside the Runtime publication boundary."""
