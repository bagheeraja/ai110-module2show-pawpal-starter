"""PawPal+ logic layer.

This module holds the backend classes for PawPal+: Owner, Pet, Task, the
supporting enums, and the Scheduler. This is a skeleton generated from the
UML in diagrams/uml.mmd -- method bodies are stubs and will be filled in
during the implementation pass.
"""

from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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
    """A task *template*.

    ``scheduled_time`` is the anchor for the task: for a one-off task it is
    the actual occurrence; for a recurring task it supplies the time-of-day
    (and, for WEEKLY, the weekday) that every generated occurrence reuses.
    Completion is tracked per calendar date in ``completed_dates`` rather
    than as a single bool, so marking one occurrence of a recurring task
    done doesn't silently complete the whole series.

    A 0-minute duration is rejected -- every task must occupy some real time
    to be schedulable/conflict-checkable. If ``scheduled_time + duration``
    crosses midnight, the occurrence is considered to belong to *both* the
    start date and the rollover (end) date, so it shows up on both days'
    plans -- see ``occurs_on``.
    """

    title: str
    task_type: TaskType
    duration_minutes: int
    priority: Priority
    scheduled_time: datetime
    recurrence: Recurrence = Recurrence.NONE
    recurrence_end_date: date | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    completed_dates: set[date] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Reject a 0 (or negative) duration -- see class docstring."""
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be greater than 0")

    def mark_complete(self, occurrence_date: date | None = None) -> None:
        """Mark the occurrence on ``occurrence_date`` complete (defaults to this task's own date)."""
        self.completed_dates.add(occurrence_date or self.scheduled_time.date())

    def is_complete_on(self, occurrence_date: date | None = None) -> bool:
        """Whether the occurrence on ``occurrence_date`` has been completed."""
        return (occurrence_date or self.scheduled_time.date()) in self.completed_dates

    def window_on(self, on: date) -> tuple[datetime, datetime] | None:
        """The (start, end) datetime pair for the occurrence touching ``on``, or None.

        Checks both an occurrence starting on ``on`` itself and one starting
        the day before that rolls over into ``on`` (see class docstring on
        midnight rollover). Shared by ``occurs_on`` and ``conflicts_with``
        so the two stay consistent.
        """
        anchor_date = self.scheduled_time.date()

        def starts_on(start_date: date) -> bool:
            if start_date < anchor_date:
                return False
            if self.recurrence == Recurrence.NONE:
                return start_date == anchor_date
            if self.recurrence_end_date is not None and start_date > self.recurrence_end_date:
                return False
            if self.recurrence == Recurrence.DAILY:
                return True
            return start_date.weekday() == anchor_date.weekday()  # WEEKLY

        if starts_on(on):
            start = datetime.combine(on, self.scheduled_time.time())
            return start, start + timedelta(minutes=self.duration_minutes)

        # An occurrence starting the day before can roll over into `on`.
        previous_date = on - timedelta(days=1)
        if starts_on(previous_date):
            start = datetime.combine(previous_date, self.scheduled_time.time())
            end = start + timedelta(minutes=self.duration_minutes)
            if end.date() == on:
                return start, end

        return None

    def occurs_on(self, target_date: date) -> bool:
        """Whether this task (recurring or not) has an occurrence touching ``target_date``.

        True if ``target_date`` matches the occurrence's start date or its
        rollover end date (see class docstring), the recurrence pattern
        includes that date, and (for recurring tasks) ``target_date`` is on
        or before ``recurrence_end_date`` when one is set.
        """
        return self.window_on(target_date) is not None

    def reschedule(self, new_scheduled_time: datetime) -> None:
        """Move a missed/overdue one-off task to a new time.

        Intended for the "missed task" recovery flow: an owner sees an
        overdue occurrence (see Scheduler.get_missed_tasks) and reschedules
        it instead of leaving it permanently missed. For a recurring task,
        this shifts the anchor for all future occurrences -- rescheduling a
        single occurrence in a series is not supported by this model.
        """
        self.scheduled_time = new_scheduled_time

    def conflicts_with(self, other: "Task", *, on: date) -> bool:
        """Whether this task's occurrence on ``on`` overlaps ``other``'s occurrence on ``on``.

        Overlap is strict: if one occurrence ends exactly when the other
        begins, that is NOT a conflict (touching, not overlapping).
        """
        my_window = self.window_on(on)
        other_window = other.window_on(on)
        if my_window is None or other_window is None:
            return False
        my_start, my_end = my_window
        other_start, other_end = other_window
        return my_start < other_end and other_start < my_end


@dataclass(frozen=True)
class TaskOccurrence:
    """A single dated instance of a Task, produced by the Scheduler.

    Occurrences are ephemeral (never stored on Pet.tasks) -- they're what
    gets displayed in a daily plan. Completion reads/writes go back through
    to the underlying template so there's one source of truth per date.

    ``pet`` is stamped on at creation time (by whichever Pet's
    get_tasks_for_date produced it) rather than stored on Task itself, so
    occurrences from different pets can be merged into one list -- e.g. for
    Scheduler.build_daily_plan_for_owner -- while still knowing which pet
    each one belongs to.
    """

    task: Task
    pet: Pet
    occurrence_date: date
    start_time: datetime
    end_time: datetime

    @property
    def completed(self) -> bool:
        """Whether this specific occurrence has been completed."""
        return self.task.is_complete_on(self.occurrence_date)

    def mark_complete(self) -> None:
        """Mark this specific occurrence complete on the underlying task."""
        self.task.mark_complete(self.occurrence_date)


@dataclass
class Pet:
    name: str
    species: str
    birthdate: date
    preferences: dict = field(default_factory=dict)
    tasks: list[Task] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def add_task(self, task: Task) -> None:
        """Attach a new task template to this pet."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task template by id (e.g. an owner deleting a mis-entered task)."""
        self.tasks = [task for task in self.tasks if task.id != task_id]

    def get_tasks_for_date(self, target_date: date) -> list[TaskOccurrence]:
        """Templates whose recurrence includes target_date, expanded via Task.occurs_on.

        Each resulting TaskOccurrence is stamped with pet=self, so callers
        that merge occurrences from multiple pets (e.g.
        Scheduler.build_daily_plan_for_owner) can still tell them apart.
        Returns [] if this pet has no tasks -- an empty result, not an error.
        This only filters/expands -- ordering, conflict-checking, and any
        time-budget constraints are Scheduler's job, not Pet's.
        """
        occurrences = []
        for task in self.tasks:
            window = task.window_on(target_date)
            if window is None:
                continue
            start_time, end_time = window
            occurrences.append(
                TaskOccurrence(
                    task=task,
                    pet=self,
                    occurrence_date=target_date,
                    start_time=start_time,
                    end_time=end_time,
                )
            )
        return occurrences


@dataclass
class Owner:
    name: str
    email: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a new pet under this owner."""
        self.pets.append(pet)

    def get_pet(self, pet_id: str) -> Pet | None:
        """Look up a pet by id -- names aren't unique (e.g. two pets both named "Max")."""
        for pet in self.pets:
            if pet.id == pet_id:
                return pet
        return None


class Scheduler:
    """Stateless scheduling logic that operates on Pet/Owner tasks.

    Owns ordering, conflict-checking, and turning templates into dated
    occurrences. Pet.get_tasks_for_date only filters/expands via
    Task.occurs_on -- it does not sort or resolve conflicts.
    """

    def build_daily_plan(
        self,
        pet: Pet,
        target_date: date,
        *,
        time_budget_minutes: int | None = None,
    ) -> list[TaskOccurrence]:
        """Not-yet-completed occurrences for target_date, for a single pet.

        Ordering: by Priority (HIGH first), and alphabetically by title as
        the initial tie-break within a priority tier. Already-completed
        occurrences (``occurrence.completed``) are excluded -- a finished
        walk shouldn't clutter the plan. If ``time_budget_minutes`` is
        given and the sorted occurrences would exceed it, lower-priority
        occurrences are dropped from the end once the running total would
        exceed the budget. Returns [] for a pet with no tasks/occurrences
        that day -- never raises for the empty case.

        For an owner with multiple pets, prefer build_daily_plan_for_owner
        over calling this once per pet and concatenating the results --
        concatenating after the fact would apply the time budget per-pet
        instead of across the owner's whole day, and would miss conflicts
        between two different pets' tasks (e.g. the owner can't walk two
        dogs at the same time even though they're different Pet objects).
        """
        return self._finalize_plan(pet.get_tasks_for_date(target_date), time_budget_minutes)

    def _finalize_plan(
        self,
        occurrences: list[TaskOccurrence],
        time_budget_minutes: int | None,
    ) -> list[TaskOccurrence]:
        """Shared not-completed filter + priority/title ordering + budget cutoff.

        Used by both build_daily_plan and build_daily_plan_for_owner so the
        two apply identical rules regardless of whether `occurrences` is
        scoped to one pet or merged across an owner's pets.
        """
        pending = [occurrence for occurrence in occurrences if not occurrence.completed]
        pending.sort(key=lambda occurrence: (-occurrence.task.priority.value, occurrence.task.title))

        if time_budget_minutes is None:
            return pending

        plan = []
        minutes_used = 0
        for occurrence in pending:
            duration = occurrence.task.duration_minutes
            if minutes_used + duration > time_budget_minutes:
                break
            plan.append(occurrence)
            minutes_used += duration
        return plan

    def build_daily_plan_for_owner(
        self,
        owner: Owner,
        target_date: date,
        *,
        time_budget_minutes: int | None = None,
    ) -> list[TaskOccurrence]:
        """Merged, ordered plan across every pet the owner has.

        Combines each pet's get_tasks_for_date(target_date) into one list
        *before* applying the not-completed filter, priority/title
        ordering, and time budget -- the same rules build_daily_plan uses,
        just applied owner-wide instead of per-pet. Each TaskOccurrence
        already carries its own `pet`, so the merged list stays groupable
        by pet for display. Feed the result into detect_conflicts to catch
        overlaps across pets, not just within one.
        """
        merged = [
            occurrence
            for pet in owner.pets
            for occurrence in pet.get_tasks_for_date(target_date)
        ]
        return self._finalize_plan(merged, time_budget_minutes)

    def detect_conflicts(
        self, occurrences: list[TaskOccurrence]
    ) -> list[tuple[TaskOccurrence, TaskOccurrence]]:
        """Pairs of occurrences whose time windows strictly overlap.

        Two occurrences that merely touch (one ends exactly when the other
        starts) are NOT a conflict. Two occurrences generated from the same
        Task (matching task.id) are never compared against each other.
        Works the same whether `occurrences` came from one pet or was
        merged across an owner's pets via build_daily_plan_for_owner.
        """
        conflicts = []
        for a, b in itertools.combinations(occurrences, 2):
            if a.task.id == b.task.id:
                continue
            if a.start_time < b.end_time and b.start_time < a.end_time:
                conflicts.append((a, b))
        return conflicts

    def expand_recurring(self, task: Task, pet: Pet, target_date: date) -> TaskOccurrence | None:
        """The occurrence of task on target_date, or None if it doesn't occur that day.

        Delegates the occurs-on-this-date decision to Task.occurs_on, which
        accounts for recurrence_end_date and midnight rollover. ``pet`` is
        stamped onto the resulting TaskOccurrence.
        """
        window = task.window_on(target_date)
        if window is None:
            return None
        start_time, end_time = window
        return TaskOccurrence(
            task=task,
            pet=pet,
            occurrence_date=target_date,
            start_time=start_time,
            end_time=end_time,
        )

    def get_missed_tasks(self, pet: Pet, as_of: date) -> list[TaskOccurrence]:
        """Past occurrences (strictly before ``as_of``) that were never completed.

        Surfaces "missed/overdue" tasks so the caller (e.g. the UI) can
        offer to reschedule them via Task.reschedule rather than letting
        them silently disappear once their date has passed.
        """
        missed = []
        for task in pet.tasks:
            for current in self._dates_to_check_for_missed(task, as_of):
                if not task.is_complete_on(current):
                    window = task.window_on(current)
                    if window is not None:
                        start_time, end_time = window
                        missed.append(
                            TaskOccurrence(
                                task=task,
                                pet=pet,
                                occurrence_date=current,
                                start_time=start_time,
                                end_time=end_time,
                            )
                        )
        return missed

    def _dates_to_check_for_missed(self, task: Task, as_of: date):
        """Calendar dates strictly before ``as_of`` worth checking for a missed occurrence.

        A one-off (NONE) task has exactly one possible occurrence date --
        its anchor -- so it's checked directly rather than walking every
        day from the anchor up to ``as_of``. That walk is unbounded in the
        number of days since the task's anchor, so an old, never-completed
        one-off task would otherwise scan hundreds of irrelevant days.
        DAILY/WEEKLY tasks still need a day-by-day walk since any
        individual day could be completed or missed independently.
        """
        anchor_date = task.scheduled_time.date()
        if task.recurrence == Recurrence.NONE:
            if anchor_date < as_of:
                yield anchor_date
            return

        current = anchor_date
        while current < as_of:
            yield current
            current += timedelta(days=1)
