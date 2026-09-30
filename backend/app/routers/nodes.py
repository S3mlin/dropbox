from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.exceptions import NameConflict, NodeNotFound, NotAFolder
from app.repository import NodeRepository, get_repo
from app.schemas import FileCreate, FolderCreate, NodeResponse, PathItem

router = APIRouter(prefix="/nodes", tags=["Nodes"])


@router.get("", response_model=list[NodeResponse])
async def list_nodes(
    parent_id: Optional[int] = Query(None, description="Omit for root"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    repo: NodeRepository = Depends(get_repo),
) -> list[NodeResponse]:
    """
    List the child nodes of the specified parent node
    If no parent_id is provided, lists the root nodes
    """
    return await repo.list_children(parent_id=parent_id, skip=skip, limit=limit)


@router.get("/{node_id}/path", response_model=list[PathItem])
async def get_path(
    node_id: int,
    repo: NodeRepository = Depends(get_repo),
) -> list[PathItem]:
    """
    Get the path from the root to the specified node
    """
    node = await repo.get_by_id(node_id=node_id)
    if node is None:
        raise NodeNotFound(node_id)
    return await repo.get_ancestors(node_id=node_id)


@router.post("/folders", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(data: FolderCreate, repo: NodeRepository = Depends(get_repo)) -> NodeResponse:
    """
    Create a new folder
    """
    if data.parent_id is not None:
        parent = await repo.get_by_id(node_id=data.parent_id)
        if not parent:
            raise NodeNotFound(data.parent_id)
        if parent.type != "folder":
            raise NotAFolder(parent.name)

    if await repo.name_exists_in_parent(data.name, data.parent_id):
        raise NameConflict(data.name)

    return await repo.create(data.name, "folder", data.parent_id)


@router.post("/files", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def create_file(data: FileCreate, repo: NodeRepository = Depends(get_repo)) -> NodeResponse:
    """
    Create a new file
    """
    if data.parent_id is not None:
        parent = await repo.get_by_id(node_id=data.parent_id)
        if not parent:
            raise NodeNotFound(data.parent_id)
        if parent.type != "folder":
            raise NotAFolder(parent.name)

    if await repo.name_exists_in_parent(data.name, data.parent_id):
        raise NameConflict(data.name)

    return await repo.create(data.name, "file", data.parent_id)


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(node_id: int, repo: NodeRepository = Depends(get_repo)) -> None:
    """
    Delete a file/folder
    """
    node = await repo.get_by_id(node_id=node_id)
    if not node:
        raise NodeNotFound(node_id)
    await repo.delete(node)
