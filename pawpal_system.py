"""PawPal+ logic layer.

This module holds the backend classes for PawPal+: Owner, Pet, Task, the
supporting enums, and the Scheduler. This is a skeleton generated from the
UML in diagrams/uml.mmd -- method bodies are stubs and will be filled in
during the implementation pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum, auto


class TaskType(Enum):
    FEEDING = auto()
    WALK = auto()
    MEDICATION = auto()
    APPOINTMENT = auto()


class Priority(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class Recurrence(Enum):
    NONE = auto()
    DAILY = auto()
    WEEKLY = auto()


@dataclass
class Task:
    title: str
    task_type: TaskType
    duration_minutes: int
    priority: Priority
    scheduled_time: datetime
    recurrence: Recurrence = Recurrence.NONE
    completed: bool = False

    def mark_complete(self) -> None:
        pass

    def conflicts_with(self, other_task: "Task") -> bool:
        pass


@dataclass
class Pet:
    name: str
    species: str
    birthdate: date
    preferences: dict = field(default_factory=dict)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        pass

    def get_tasks_for_date(self, target_date: date) -> list[Task]:
        pass


@dataclass
class Owner:
    name: str
    email: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        pass

    def get_pet(self, name: str) -> Pet | None:
        pass


class Scheduler:
    """Stateless scheduling logic that operates on a Pet's tasks."""

    def build_daily_plan(self, pet: Pet, target_date: date) -> list[Task]:
        pass

    def detect_conflicts(self, tasks: list[Task]) -> list[Task]:
        pass

    def expand_recurring(self, task: Task, target_date: date) -> list[Task]:
        pass
