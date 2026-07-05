from datetime import date, datetime

from pawpal_system import Pet, Priority, Task, TaskType


def test_mark_complete_changes_task_status():
    task = Task(
        title="Morning walk",
        task_type=TaskType.WALK,
        duration_minutes=20,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 8, 0),
    )

    assert not task.is_complete_on(date(2026, 7, 5))

    task.mark_complete()

    assert task.is_complete_on(date(2026, 7, 5))


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog", birthdate=date(2020, 3, 14))
    task = Task(
        title="Breakfast",
        task_type=TaskType.FEEDING,
        duration_minutes=10,
        priority=Priority.HIGH,
        scheduled_time=datetime(2026, 7, 5, 7, 30),
    )

    assert len(pet.tasks) == 0

    pet.add_task(task)

    assert len(pet.tasks) == 1
