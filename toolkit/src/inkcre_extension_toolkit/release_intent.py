"""Publisher-owned exact Release intent, separate from executable package metadata."""

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .contracts import PrepareReleaseRequest
from .semantic import ContractModel, StrictSemVer


class ReleaseIntent(ContractModel):
    version: StrictSemVer
    required_native_formats: tuple[Literal["python", "module_federation"], ...] = Field(
        min_length=1, max_length=2
    )

    @model_validator(mode="after")
    def formats_are_unique(self) -> "ReleaseIntent":
        if len(set(self.required_native_formats)) != len(self.required_native_formats):
            raise ValueError("required_native_formats must not contain duplicates")
        return self

    def prepare(self, request: PrepareReleaseRequest) -> PrepareReleaseRequest:
        if request.version != self.version:
            raise ValueError("producer version differs from the exact Release intent")
        if request.required_native_formats is not None and set(
            request.required_native_formats.root
        ) != set(self.required_native_formats):
            raise ValueError("producer native formats differ from the Release intent")
        return PrepareReleaseRequest.model_validate(
            {**request.model_dump(), "required_native_formats": self.required_native_formats}
        )


def load_release_intent(path: Path) -> ReleaseIntent:
    return ReleaseIntent.model_validate_json(path.read_text(encoding="utf-8"))
