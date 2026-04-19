from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    token: str
    original_filename: str
    file_size: int
    expires_at: str
    one_time_download: bool
    passcode_set: bool
