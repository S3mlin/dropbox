from app.db import Base
from sqlalchemy import (
    CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Index
)
from sqlalchemy.sql import func


class Node(Base):
    """
    Represents a node in the filesystem, which can be either a file or a folder.
    On delete cascade for child nodes when a parent folder is deleted.
    """
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    type = Column(String(10), nullable=False)
    parent_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint("type IN ('file', 'folder')", name="ck_node_type"),
        Index("ix_nodes_name", "name"),
    )
