"""Terminal testing ground for pawpal_system.py -- not the final UI.

Creates an owner with two pets and a handful of tasks, then prints
today's schedule to verify the backend logic works end to end.
"""

from datetime import date, datetime, time

from pawpal_system import Owner, Pet, Priority, Recurrence, Scheduler, Task, TaskType

TODAY = date.today()


def at(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(TODAY, time(hour, minute))


def main() -> None:
    owner = Owner(name="Jordan Ames", email="jordan@example.com")

    mochi = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    biscuit = Pet(name="Biscuit", species="cat", birthdate=date(2021, 6, 1))
    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    mochi.add_task(
        Task(
            title="Morning walk",
            task_type=TaskType.WALK,
            duration_minutes=20,
            priority=Priority.HIGH,
            scheduled_time=at(8, 0),
        )
    )
    mochi.add_task(
        Task(
            title="Breakfast",
            task_type=TaskType.FEEDING,
            duration_minutes=10,
            priority=Priority.HIGH,
            scheduled_time=at(7, 30),
            recurrence=Recurrence.DAILY,
        )
    )
    biscuit.add_task(
        Task(
            title="Flea medication",
            task_type=TaskType.MEDICATION,
            duration_minutes=5,
            priority=Priority.MEDIUM,
            scheduled_time=at(9, 0),
        )
    )
    biscuit.add_task(
        Task(
            title="Vet checkup",
            task_type=TaskType.APPOINTMENT,
            duration_minutes=30,
            priority=Priority.MEDIUM,
            scheduled_time=at(14, 0),
        )
    )

    scheduler = Scheduler()
    plan = scheduler.build_daily_plan_for_owner(owner, TODAY)

    print(f"Today's Schedule -- {TODAY.isoformat()}")
    print("=" * 40)
    for occurrence in plan:
        start = occurrence.start_time.strftime("%I:%M %p")
        print(
            f"{start}  {occurrence.pet.name:<8} {occurrence.task.title:<18} "
            f"[{occurrence.task.priority.name}]"
        )

    conflicts = scheduler.detect_conflicts(plan)
    if conflicts:
        print("\nConflicts detected:")
        for a, b in conflicts:
            print(f"  {a.pet.name}'s {a.task.title} overlaps {b.pet.name}'s {b.task.title}")


if __name__ == "__main__":
    main()
