"""Direct upload metadata; file contents never pass through Vercel's request body."""

from pydantic import BaseModel, Field


class PrepareUpload(BaseModel):
    original_name: str = Field(min_length=1, max_length=255, examples=["เอกสาร.pdf"])
    content_type: str = Field(max_length=100, examples=["application/pdf"])
    size_bytes: int = Field(gt=0, examples=[1024])
    slot_no: int | None = Field(default=None, ge=1, examples=[1])


class CompleteUpload(BaseModel):
    ticket: str = Field(min_length=1, max_length=4096, examples=["signed-upload-ticket"])
