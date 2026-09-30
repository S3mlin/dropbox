from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

FORBIDDEN = set('/\\:*?"<>|\0')


def check_name(name: str) -> str:
    """
    Proper file/folder name validation
    """
    name = name.strip()
    if not name:
        raise ValueError("Name cannot be empty")
    if any(char in FORBIDDEN for char in name):
        raise ValueError(f"Name contains forbidden characters: {FORBIDDEN}")
    return name


class NodeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[int] = Field(None)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return check_name(v)


class FolderCreate(NodeCreate):
    pass


class FileCreate(NodeCreate):
    pass


class NodeResponse(BaseModel):
    id: int
    name: str
    type: str
    parent_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class PathItem(BaseModel):
    """
    Item in the filesystem path, which can be a file or a folder.
    """
    id: Optional[int] = None
    name: str

    model_config = {"from_attributes": True}
