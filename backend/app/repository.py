from fastapi import Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Node


class NodeRepository:
    """
    Repository class for managing Node entities in the database
    Methods for CRUD operations and some queries
    """
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, node_id: int) -> Node | None:
        """
        Retrieve a node by its ID
        """
        return await self.session.get(Node, node_id)

    async def list_children(self, parent_id: int | None, skip: int = 0, limit: int = 200) -> list[Node]:
        """
        List child nodes of a given parent node
        Order by type (folders first) and then by name
        """
        stmt = (
            select(Node)
            .where(Node.parent_id == parent_id)
            .order_by(Node.type.desc(), Node.name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_ancestors(self, node_id: int) -> list[Node]:
        """
        Get file/folder path (ancestors) for a given node
        Follows parent_id links up to the root node
        """
        path: list[Node] = []
        current_id: int | None = node_id

        while current_id is not None:
            node = await self.session.get(Node, current_id)
            if node is None:
                break
            path.append(node)
            current_id = node.parent_id

        path.reverse()
        return path

    async def name_exists_in_parent(self, name: str, parent_id: int | None) -> bool:
        """
        Check for name uniqueness within a given parent folder
        """
        stmt = select(Node).where(and_(Node.name == name, Node.parent_id == parent_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def search_extract(self, name: str, folder_id: int | None = None) -> list[Node]:
        """
        Search for files by name within a folder
        """
        stmt = select(Node).where(Node.type == "file", Node.name == name)
        if folder_id is not None:
            stmt = stmt.where(Node.parent_id == folder_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def autocomplete(self, prefix: str, limit: int = 10) -> list[Node]:
        """
        Autocomplete file names based on a given prefix
        """
        stmt = (
            select(Node)
            .where(Node.type == "file", Node.name.like(f"{prefix}%"))
            .order_by(Node.name)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, name: str, node_type: str, parent_id: int | None = None) -> Node:
        """
        Create a new node (file or folder) in the filesystem
        """
        node = Node(name=name, type=node_type, parent_id=parent_id)
        self.session.add(node)
        await self.session.commit()
        await self.session.refresh(node)
        return node

    async def delete(self, node: Node) -> None:
        """
        Delete a node (file or folder) from the filesystem
        """
        await self.session.delete(node)
        await self.session.commit()


async def get_repo(db: AsyncSession = Depends(get_db)) -> NodeRepository:
        """
        Get an instance of the NodeRepository
        """
        return NodeRepository(db)