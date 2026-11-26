from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from backend.api.auth import handle_auth_validation_error
from backend.api.routes import router

app = FastAPI(exception_handlers={RequestValidationError: handle_auth_validation_error})
app.include_router(router)
