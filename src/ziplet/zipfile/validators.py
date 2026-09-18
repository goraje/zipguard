"""Composable metadata validators for policy-enabled extraction."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Protocol, cast

from ziplet.zipfile.assessment import ExtractionContext, ValidationState
from ziplet.zipfile.extract import ExtractViolation
from ziplet.zipfile.info import ZipInfo


class MemberValidator(Protocol):
    """Protocol implemented by one metadata-only member validator."""

    def __call__(
        self,
        info: ZipInfo,
        target: Path,
        context: ExtractionContext,
        state: ValidationState,
    ) -> Iterable[ExtractViolation]: ...


class ValidatorPipeline:
    """Run validators in a deterministic order."""

    def __init__(self, validators: Iterable[MemberValidator]) -> None:
        self._validators = tuple(validators)

    def validate(
        self,
        info: ZipInfo,
        target: Path,
        context: ExtractionContext,
        state: ValidationState,
    ) -> list[ExtractViolation]:
        violations: list[ExtractViolation] = []
        for validator in self._validators:
            violations.extend(validator(info, target, context, state))
        return violations


def custom_validator(callback: Callable[[ZipInfo, Path], None]) -> MemberValidator:
    """Adapt the established two-argument custom-validator API."""

    def validate(
        info: ZipInfo,
        target: Path,
        _context: ExtractionContext,
        _state: ValidationState,
    ) -> Iterable[ExtractViolation]:
        callback(info, target)
        return ()

    return cast(MemberValidator, validate)
