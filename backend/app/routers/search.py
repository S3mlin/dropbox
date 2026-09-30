from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.repository import NodeRepository, get_repo
from app.schemas import NodeResponse

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=list[NodeResponse])
async def search_extract(
    name: str = Query(..., description="Exact name to find"),
    folder_id: Optional[int] = Query(None, description="Limit to folder's direct children"),
    repo: NodeRepository = Depends(get_repo),
) -> list[NodeResponse]:
    """
    Search for exact file names within a folder
    """
    return await repo.search_extract(name=name, folder_id=folder_id)


@router.get("/autocomplete", response_model=list[NodeResponse])
async def autocomplete(
    q: str = Query(..., min_length=1, description="Name prefix"),
    repo: NodeRepository = Depends(get_repo),
) -> list[NodeResponse]:
    """
    Autocomplete file names based on a given prefix
    """
    return await repo.autocomplete(q)
