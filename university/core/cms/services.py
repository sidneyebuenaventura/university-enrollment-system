from .models import Room, Subject, Class, ClassGradeState


def room_delete(*, room: Room) -> None:
    room.soft_delete()


def class_delete(*, klass: Class) -> None:
    klass.soft_delete()


def subject_delete(*, subject: Subject) -> None:
    subject.soft_delete()


def class_grade_state_update(
    *, klass: Class, state: ClassGradeState.States, fields: list[str] = None
):
    if not hasattr(klass, "grade_states"):
        ClassGradeState.objects.create(klass=klass)

    grade_states = klass.grade_states

    for field in fields:
        setattr(grade_states, f"{field}_state", state)

    grade_states.save()
