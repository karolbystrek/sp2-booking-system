from fastapi import FastAPI

from app.database import Base, engine
from app.api import admin_endpoints, specialist_endpoints, user_endpoints
from app.seed import seed

Base.metadata.create_all(bind=engine)
seed()

app = FastAPI(title="Appointment Booking System")

app.include_router(user_endpoints.router)
app.include_router(specialist_endpoints.router)
app.include_router(admin_endpoints.router)
