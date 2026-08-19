"""Extension-facing lifecycle bound directly to Core's rich model."""

from __future__ import annotations

import typing

import pydantic

from .errors import ExtensionLifecycleError, translate_host_model_error


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
        cls.__configcls__.model_validate(model.config)
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
        config = cls.__configcls__.model_validate(value)
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
        def mutate(raw: dict[str, typing.Any]) -> dict[str, typing.Any]:
            updated = transform(cls.__statecls__.model_validate(raw))
            if not isinstance(updated, cls.__statecls__):
                raise TypeError("Extension state transform returned the wrong model")
            return updated.model_dump(mode="json")

        try:
            raw = cls._model().mutate_state(mutate)
        except Exception as error:
            translate_host_model_error(error)
        return cls.__statecls__.model_validate(raw)

    @classmethod
    def mutate_config_and_state(
        cls, transform: typing.Callable[[ConfigT, StateT], tuple[ConfigT, StateT]]
    ) -> tuple[ConfigT, StateT]:
        def mutate(
            config: dict[str, typing.Any], state: dict[str, typing.Any]
        ) -> tuple[dict[str, typing.Any], dict[str, typing.Any]]:
            new_config, new_state = transform(
                cls.__configcls__.model_validate(config), cls.__statecls__.model_validate(state)
            )
            if not isinstance(new_config, cls.__configcls__) or not isinstance(
                new_state, cls.__statecls__
            ):
                raise TypeError("Extension config/state transform returned the wrong models")
            return new_config.model_dump(mode="json"), new_state.model_dump(mode="json")

        try:
            config, state = cls._model().mutate_config_and_state(mutate)
        except Exception as error:
            translate_host_model_error(error)
        return cls.__configcls__.model_validate(config), cls.__statecls__.model_validate(state)

    @classmethod
    def on_start(cls, app: typing.Any) -> None:
        """Validate config and atomically publish concrete Core contributions."""
        import fastapi
        from app.business.peer import PeerManager

        from .publication import (
            ExtensionPublicationSnapshot,
            PublicHTTPRouteClaim,
        )

        snapshot = ExtensionPublicationSnapshot.capture(app)
        if cls.runtime_active():
            snapshot.rollback()
            raise ExtensionLifecycleError(f"Extension {cls.__extid__} is already active")
        publication = None
        try:
            cls.__configcls__.model_validate(cls._model().config)
            router = fastapi.APIRouter(
                prefix=f"/{cls.__extid__}", dependencies=cls.api_dependencies()
            )
            cls._register_apis(router)
            registered_routes = tuple(router.routes)
            app.include_router(router, tags=["extension", cls.__extid__])
            cls._init_sources()
            cls._init_resolvers()
            for inbound in cls.peer_inbounds():
                PeerManager.register_inbound(inbound)
            publication = snapshot.finish()
            publication.public_http_claim = PublicHTTPRouteClaim.acquire(
                cls.__extid__, cls.public_http_routes(), registered_routes
            )
            publication.activate_source_types()
            try:
                cls.__model__ = cls._model().update_config_schema(dict(cls.__configschema__))
            except Exception as error:
                translate_host_model_error(error)
        except Exception:
            if publication is None:
                snapshot.rollback()
            else:
                publication.restore()
            raise
        cls.__runtime_publication__ = publication

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
        return publication is not None and not publication.restored

    @classmethod
    def unpublish(cls) -> None:
        publication = cls.__dict__.get("__runtime_publication__")
        if publication is not None:
            publication.restore()

    @classmethod
    def release_runtime(cls) -> None:
        if "__runtime_publication__" in cls.__dict__:
            del cls.__runtime_publication__

    @classmethod
    async def on_close(cls) -> None:
        """Withdraw resources owned outside the Runtime publication boundary."""
