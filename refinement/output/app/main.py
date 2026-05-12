from fastapi import FastAPI

from app.database import Base
from app.database import SessionLocal
from app.database import engine
from app.routers.admin import router as admin_router
from app.routers.bookings import router as bookings_router
from app.routers.slots import router as slots_router
from app.seed import seed_data

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Appointment Booking System")

app.include_router(slots_router)
app.include_router(bookings_router)
app.include_router(admin_router)


db = SessionLocal()
seed_data(db)
db.close()


@app.get("/")
def health_check():
    return {"status": "ok"}