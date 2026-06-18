from models import SlotStatus


def test_get_available_slots_returns_only_available_status(service, repo, slot_factory):
    available_slot = slot_factory(slot_id=1, status=SlotStatus.AVAILABLE)
    booked_slot = slot_factory(slot_id=2, status=SlotStatus.BOOKED)
    blocked_slot = slot_factory(slot_id=3, status=SlotStatus.BLOCKED)
    repo.add_slot(available_slot)
    repo.add_slot(booked_slot)
    repo.add_slot(blocked_slot)

    result = service.get_available_slots(
        specialist_id=10,
        date=available_slot.start_time.date(),
    )

    assert [slot.id for slot in result] == [1]
    assert all(slot.status == SlotStatus.AVAILABLE for slot in result)


def test_get_available_slots_filters_by_specialist(service, repo, slot_factory):
    target_slot = slot_factory(slot_id=1, specialist_id=10)
    other_specialist_slot = slot_factory(slot_id=2, specialist_id=20)
    repo.add_slot(target_slot)
    repo.add_slot(other_specialist_slot)

    result = service.get_available_slots(
        specialist_id=10,
        date=target_slot.start_time.date(),
    )

    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].specialist_id == 10


def test_get_available_slots_filters_by_date(service, repo, slot_factory):
    target_day_slot = slot_factory(slot_id=1, hours_from_now=48)
    other_day_slot = slot_factory(slot_id=2, hours_from_now=72)
    repo.add_slot(target_day_slot)
    repo.add_slot(other_day_slot)

    result = service.get_available_slots(
        specialist_id=10,
        date=target_day_slot.start_time.date(),
    )

    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].start_time.date() == target_day_slot.start_time.date()


def test_get_available_slots_returns_empty_list_when_no_slots_match(
    service, repo, slot_factory
):
    slot = slot_factory(slot_id=1, specialist_id=20)
    repo.add_slot(slot)

    result = service.get_available_slots(
        specialist_id=10,
        date=slot.start_time.date(),
    )

    assert result == []


def test_get_available_slots_excludes_all_unavailable_statuses(
    service, repo, slot_factory
):
    for slot_id, status in enumerate(
        [SlotStatus.BOOKED, SlotStatus.BLOCKED, SlotStatus.COMPLETED],
        start=1,
    ):
        repo.add_slot(slot_factory(slot_id=slot_id, status=status))

    result = service.get_available_slots(
        specialist_id=10,
        date=repo.get_slot(1).start_time.date(),
    )

    assert result == []
