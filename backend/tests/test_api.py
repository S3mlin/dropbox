import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db import Base, get_db
from app.main import app


@pytest_asyncio.fixture(loop_scope="function")
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


# HELPERS

async def make_folder(client: AsyncClient, name: str, parent_id=None) -> dict:
    """
    Create a folder and return the response JSON
    """
    res = await client.post(
        "/api/nodes/folders",
        json={"name": name, "parent_id": parent_id},
    )
    assert res.status_code == 201, res.text
    return res.json()


async def make_file(client: AsyncClient, name: str, parent_id=None) -> dict:
    """
    Create a file and return the response JSON
    """
    res = await client.post(
        "/api/nodes/files",
        json={"name": name, "parent_id": parent_id},
    )
    assert res.status_code == 201, res.text
    return res.json()


# NODES

class TestListNodes:
    async def test_lists_direct_children_only(self, client):
        """
        Nodes inside a subfolder must NOT appear in the parent listing
        Verifies that the parent_id filter is applied correctly
        """
        parent = await make_folder(client, "parent")
        child_folder = await make_folder(client, "child", parent["id"])
        await make_file(client, "deep.txt", child_folder["id"])

        res = await client.get(f"/api/nodes?parent_id={parent['id']}")
        assert res.status_code == 200
        items = res.json()
        # Only the direct child folder — the grandchild file must not appear
        assert len(items) == 1
        assert items[0]["name"] == "child"


class TestCreateFolder:
    async def test_creates_folder_at_root(self, client):
        res = await client.post("/api/nodes/folders", json={"name": "Documents"})
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Documents"
        assert data["type"] == "folder"
        assert data["parent_id"] is None
        assert "id" in data
        assert "created_at" in data

    async def test_creates_nested_folder(self, client):
        parent = await make_folder(client, "parent")
        res = await client.post(
            "/api/nodes/folders",
            json={"name": "child", "parent_id": parent["id"]},
        )
        assert res.status_code == 201
        assert res.json()["parent_id"] == parent["id"]

    async def test_duplicate_name_in_same_folder_returns_409(self, client):
        await make_folder(client, "Documents")
        res = await client.post("/api/nodes/folders", json={"name": "Documents"})
        assert res.status_code == 409


class TestCreateFile:
    async def test_creates_file_inside_folder(self, client):
        folder = await make_folder(client, "Documents")
        res = await client.post(
            "/api/nodes/files",
            json={"name": "report.txt", "parent_id": folder["id"]},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "report.txt"
        assert data["type"] == "file"
        assert data["parent_id"] == folder["id"]

    async def test_cannot_create_file_inside_a_file(self, client):
        folder = await make_folder(client, "Documents")
        file = await make_file(client, "report.txt", folder["id"])
        res = await client.post(
            "/api/nodes/files",
            json={"name": "nested.txt", "parent_id": file["id"]},
        )
        assert res.status_code == 400


class TestGetPath:
    async def test_path_for_root_level_folder(self, client):
        folder = await make_folder(client, "Documents")
        res = await client.get(f"/api/nodes/{folder['id']}/path")
        assert res.status_code == 200
        path = res.json()
        assert len(path) == 1
        assert path[0]["name"] == "Documents"

    async def test_path_reflects_full_ancestor_chain(self, client):
        docs = await make_folder(client, "Documents")
        year = await make_folder(client, "2024", docs["id"])
        note = await make_file(client, "notes.txt", year["id"])

        res = await client.get(f"/api/nodes/{note['id']}/path")
        assert res.status_code == 200
        path = res.json()
        assert [p["name"] for p in path] == ["Documents", "2024", "notes.txt"]

    async def test_returns_404_for_missing_node(self, client):
        res = await client.get("/api/nodes/99999/path")
        assert res.status_code == 404


class TestDeleteNode:
    async def test_delete_file(self, client):
        folder = await make_folder(client, "Documents")
        file = await make_file(client, "report.txt", folder["id"])

        res = await client.delete(f"/api/nodes/{file['id']}")
        assert res.status_code == 204

        # Verify the file is gone from the folder listing
        items = (await client.get(f"/api/nodes?parent_id={folder['id']}")).json()
        assert len(items) == 0

    async def test_delete_folder_cascades_to_all_descendants(self, client):
        folder = await make_folder(client, "Documents")
        sub = await make_folder(client, "SubFolder", folder["id"])
        await make_file(client, "file1.txt", folder["id"])
        await make_file(client, "file2.txt", sub["id"])  # grandchild

        res = await client.delete(f"/api/nodes/{folder['id']}")
        assert res.status_code == 204

        # Root is empty — folder and all descendants are gone
        root_items = (await client.get("/api/nodes")).json()
        assert root_items == []

    async def test_delete_returns_404_for_missing_node(self, client):
        res = await client.delete("/api/nodes/99999")
        assert res.status_code == 404


# SEARCH

class TestSearchByPrefix:
    async def test_returns_files_starting_with_prefix(self, client):
        folder = await make_folder(client, "docs")
        await make_file(client, "budget.xlsx", folder["id"])
        await make_file(client, "budget_2024.xlsx", folder["id"])
        await make_file(client, "report.txt", folder["id"])

        res = await client.get("/api/search/autocomplete?q=budget")
        assert res.status_code == 200
        results = res.json()
        assert len(results) == 2
        assert all(r["name"].startswith("budget") for r in results)


    async def test_excludes_folders_from_results(self, client):
        await make_folder(client, "reports")
        folder = await make_folder(client, "docs")
        await make_file(client, "report.txt", folder["id"])

        res = await client.get("/api/search/autocomplete?q=rep")
        results = res.json()
        assert len(results) == 1
        assert results[0]["type"] == "file"
        assert results[0]["name"] == "report.txt"


    async def test_limit_caps_results_for_dropdown(self, client):
        folder = await make_folder(client, "docs")
        for i in range(15):
            await make_file(client, f"file{i:02}.txt", folder["id"])

        res = await client.get("/api/search/autocomplete?q=file&limit=10")
        assert res.status_code == 200
        assert len(res.json()) == 10


    async def test_returns_empty_list_for_no_matches(self, client):
        res = await client.get("/api/search/autocomplete?q=zzz")
        assert res.status_code == 200
        assert res.json() == []


    async def test_results_are_sorted_alphabetically(self, client):
        folder = await make_folder(client, "docs")
        await make_file(client, "report_c.txt", folder["id"])
        await make_file(client, "report_a.txt", folder["id"])
        await make_file(client, "report_b.txt", folder["id"])

        res = await client.get("/api/search/autocomplete?q=report")
        names = [r["name"] for r in res.json()]
        assert names == sorted(names)


class TestSearchExact:
    async def test_finds_node_by_exact_name(self, client):
        folder = await make_folder(client, "docs")
        await make_file(client, "report.txt", folder["id"])
        await make_file(client, "report_final.txt", folder["id"])

        res = await client.get("/api/search?name=report.txt")
        assert res.status_code == 200
        results = res.json()
        assert len(results) == 1
        assert results[0]["name"] == "report.txt"

    async def test_scoped_search_only_checks_direct_children(self, client):
        folder_a = await make_folder(client, "FolderA")
        folder_b = await make_folder(client, "FolderB")
        await make_file(client, "report.txt", folder_a["id"])
        await make_file(client, "report.txt", folder_b["id"])

        res = await client.get(
            f"/api/search?name=report.txt&folder_id={folder_a['id']}"
        )
        results = res.json()
        # Scoped to folder_a — only one result even though both folders have the file
        assert len(results) == 1
        assert results[0]["parent_id"] == folder_a["id"]