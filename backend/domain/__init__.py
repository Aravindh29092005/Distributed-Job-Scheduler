"""Domain layer — pure Python entities, framework-agnostic.

These dataclasses define the canonical shape of business concepts without
any SQLAlchemy, FastAPI, or Pydantic dependency. Services operate on domain
objects; repositories convert ORM models to/from domain objects.

Why a separate domain layer?
  - Testable without a DB — unit tests instantiate domain objects directly.
  - Framework-agnostic — if we swap FastAPI for something else, domain stays.
  - Forces explicit mapping: ORM ↔ domain ↔ schema keeps each layer honest.
"""
from backend.domain.entities import (
    JobEntity,
    QueueEntity,
    OrganizationEntity,
    ProjectEntity,
    WorkerEntity,
    DLQEntry,
)

__all__ = [
    "JobEntity",
    "QueueEntity",
    "OrganizationEntity",
    "ProjectEntity",
    "WorkerEntity",
    "DLQEntry",
]
