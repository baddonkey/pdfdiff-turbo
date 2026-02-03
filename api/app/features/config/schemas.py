from pydantic import BaseModel


class AppConfigMessage(BaseModel):
    allow_registration: bool
    enable_dropzone: bool


class AppConfigUpdateCommand(BaseModel):
    allow_registration: bool | None = None
    enable_dropzone: bool | None = None
