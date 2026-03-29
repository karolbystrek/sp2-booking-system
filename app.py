from datetime import datetime, timedelta

from models import Slot, SlotStatus
from repository import InMemoryRepository
from services import BookingService, BookingError

MENU = """
=== Appointment Booking System ===
1. View available slots
2. Book a slot
3. Cancel a booking
4. View my bookings
5. Exit
"""


def seed_slots(repo):
    now = datetime.utcnow()
    base = now + timedelta(hours=48)
    for i in range(1, 6):
        start = base + timedelta(hours=i)
        slot = Slot(
            id=i,
            specialist_id=10,
            start_time=start,
            end_time=start + timedelta(minutes=30),
        )
        repo.add_slot(slot)


def read_int(prompt):
    try:
        return int(input(prompt))
    except ValueError:
        return None


def view_available_slots(service):
    specialist_id = read_int("Specialist ID: ")
    if specialist_id is None:
        print("Invalid specialist ID.")
        return
    date_str = input("Date (YYYY-MM-DD) [leave empty for all seeded]: ").strip()
    if date_str:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format.")
            return
    else:
        date = (datetime.utcnow() + timedelta(hours=48)).date()

    slots = service.get_available_slots(specialist_id, date)
    if not slots:
        print("No available slots found.")
        return
    for s in slots:
        print(f"  Slot {s.id}: {s.start_time:%Y-%m-%d %H:%M} - {s.end_time:%H:%M}")


def book_slot(service, user_id):
    slot_id = read_int("Slot ID to book: ")
    if slot_id is None:
        print("Invalid slot ID.")
        return
    try:
        booking = service.book_slot(user_id, slot_id)
        print(
            f"  Booking created: id={booking.id}, slot={booking.slot_id}, status={booking.status.value}"
        )
    except BookingError as e:
        print(f"  Error: {e}")


def cancel_booking(service, user_id):
    booking_id = read_int("Booking ID to cancel: ")
    if booking_id is None:
        print("Invalid booking ID.")
        return
    try:
        booking = service.cancel_booking(user_id, booking_id)
        print(f"  Booking {booking.id} cancelled. Status: {booking.status.value}")
    except BookingError as e:
        print(f"  Error: {e}")


def view_my_bookings(repo, user_id):
    bookings = [b for b in repo.bookings.values() if b.user_id == user_id]
    if not bookings:
        print("No bookings found.")
        return
    for b in bookings:
        slot = repo.get_slot(b.slot_id)
        slot_info = f"{slot.start_time:%Y-%m-%d %H:%M}" if slot else "unknown"
        print(
            f"  Booking {b.id}: slot={b.slot_id} ({slot_info}), status={b.status.value}"
        )


def main():
    repo = InMemoryRepository()
    service = BookingService(repo)
    seed_slots(repo)

    user_id = read_int("Enter your user ID: ")
    if user_id is None:
        print("Invalid user ID.")
        return

    print(f"Logged in as user {user_id}.")

    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()

        if choice == "1":
            view_available_slots(service)
        elif choice == "2":
            book_slot(service, user_id)
        elif choice == "3":
            cancel_booking(service, user_id)
        elif choice == "4":
            view_my_bookings(repo, user_id)
        elif choice == "5":
            print("Goodbye.")
            break
        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()
