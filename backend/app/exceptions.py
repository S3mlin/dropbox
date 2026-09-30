from fastapi import HTTPException, status


class NodeNotFound(HTTPException):
    def __init__(self, node_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Node {node_id} not found",
        )


class NotAFolder(HTTPException):
    def __init__(self, name: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"{name} is a file, not a folder",
        )


class NameConflict(HTTPException):
    def __init__(self, name: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT, detail=f"{name} already exists in this location",
        )
