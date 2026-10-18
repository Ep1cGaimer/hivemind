"""Human-facing shared memory operations over the graph store."""

from __future__ import annotations

from datetime import datetime, timezone
import secrets
from typing import Any, Iterable

from .auth import Identity
from .domain import ProjectMember, WorkspaceMemory, WorkspaceProject, deterministic_id, record_to_dict
from .store import StoreError


class MemoryWorkspace:
    """Expose a small editable memory collection without graph terminology."""

    MAX_TITLE = 140
    MAX_BODY = 20_000
    MAX_TAGS = 12

    def __init__(self, store: Any) -> None:
        self.store = store

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _clean_tags(tags: Any) -> tuple[str, ...] | None:
        if tags is None:
            return ()
        if isinstance(tags, str):
            values: Iterable[Any] = tags.split(",")
        elif isinstance(tags, (list, tuple)):
            values = tags
        else:
            return None
        clean: list[str] = []
        for value in values:
            if not isinstance(value, str):
                return None
            item = value.strip()
            if item and item not in clean:
                clean.append(item[:40])
        if len(clean) > MemoryWorkspace.MAX_TAGS:
            return None
        return tuple(clean)

    @classmethod
    def _validate_text(cls, title: Any, body: Any) -> dict[str, Any] | None:
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > cls.MAX_TITLE:
            return {"ok": False, "error": {"code": "INVALID_TITLE", "message": "Title is required and must be at most 140 characters"}}
        if not isinstance(body, str) or not body.strip() or len(body.strip()) > cls.MAX_BODY:
            return {"ok": False, "error": {"code": "INVALID_BODY", "message": "Memory text is required and must be at most 20,000 characters"}}
        return None

    @staticmethod
    def _public(memory: WorkspaceMemory) -> dict[str, Any]:
        result = record_to_dict(memory)
        result.pop("node_type", None)
        return result

    def _all(self) -> list[WorkspaceMemory]:
        return [item for item in self.store.nodes("WorkspaceMemory") if isinstance(item, WorkspaceMemory)]

    def _latest(self, memory_key: str, workspace_project_id: str | None = None) -> WorkspaceMemory | None:
        values = [
            item
            for item in self._all()
            if item.memory_key == memory_key
            and not item.archived
            and (workspace_project_id is None or item.workspace_project_id == workspace_project_id)
        ]
        return max(values, key=lambda item: (item.version, item.updated_at), default=None)

    def _resolve(self, memory_id: Any, workspace_project_id: str | None = None) -> WorkspaceMemory | None:
        if not isinstance(memory_id, str) or not memory_id.strip():
            return None
        exact = self.store.get_node(memory_id)
        if isinstance(exact, WorkspaceMemory):
            if workspace_project_id is not None and exact.workspace_project_id != workspace_project_id:
                return None
            return self._latest(exact.memory_key, exact.workspace_project_id) or exact
        return self._latest(memory_id, workspace_project_id)

    def list_memories(self, workspace_project_id: str = "project:default") -> dict[str, Any]:
        latest: dict[str, WorkspaceMemory] = {}
        for item in self._all():
            if item.archived or item.workspace_project_id != workspace_project_id:
                continue
            previous = latest.get(item.memory_key)
            if previous is None or (item.version, item.updated_at) > (previous.version, previous.updated_at):
                latest[item.memory_key] = item
        values = sorted(latest.values(), key=lambda item: (item.updated_at, item.id), reverse=True)
        return {"ok": True, "memories": [self._public(item) for item in values], "count": len(values)}

    def get_memory(self, memory_id: Any, workspace_project_id: str = "project:default") -> dict[str, Any]:
        memory = self._resolve(memory_id, workspace_project_id)
        if memory is None:
            return {"ok": False, "error": {"code": "MEMORY_NOT_FOUND", "message": "Memory was not found"}}
        return {"ok": True, "memory": self._public(memory)}

    def create(
        self,
        identity: Identity,
        title: Any,
        body: Any,
        tags: Any = None,
        workspace_project_id: str = "project:default",
    ) -> dict[str, Any]:
        invalid = self._validate_text(title, body)
        if invalid:
            return invalid
        clean_tags = self._clean_tags(tags)
        if clean_tags is None:
            return {"ok": False, "error": {"code": "INVALID_TAGS", "message": "Tags must be at most 12 text labels"}}
        now = self._now()
        memory_key = f"memory:workspace:{secrets.token_hex(8)}"
        memory = WorkspaceMemory(
            id=f"{memory_key}:v1",
            memory_key=memory_key,
            tenant_id=self.store.tenant_id,
            project_id=self.store.project_id,
            owner_user_id=identity.user_id,
            title=title.strip(),
            body=body.strip(),
            tags=clean_tags,
            created_at=now,
            updated_at=now,
            version=1,
            workspace_project_id=workspace_project_id,
        )
        try:
            self.store.add_node(memory)
        except (StoreError, TypeError, ValueError) as exc:
            return {"ok": False, "error": {"code": "MEMORY_CREATE_FAILED", "message": str(exc)}}
        return {"ok": True, "memory": self._public(memory), "created": True}

    def edit(
        self,
        identity: Identity,
        memory_id: Any,
        title: Any,
        body: Any,
        tags: Any = None,
        workspace_project_id: str = "project:default",
    ) -> dict[str, Any]:
        current = self._resolve(memory_id, workspace_project_id)
        if current is None:
            return {"ok": False, "error": {"code": "MEMORY_NOT_FOUND", "message": "Memory was not found"}}
        if current.owner_user_id != identity.user_id and identity.role != "operator":
            return {"ok": False, "error": {"code": "FORBIDDEN", "message": "Only the memory owner or an operator can edit it"}}
        next_title = current.title if title is None else title
        next_body = current.body if body is None else body
        invalid = self._validate_text(next_title, next_body)
        if invalid:
            return invalid
        clean_tags = current.tags if tags is None else self._clean_tags(tags)
        if clean_tags is None:
            return {"ok": False, "error": {"code": "INVALID_TAGS", "message": "Tags must be at most 12 text labels"}}
        now = self._now()
        edited = WorkspaceMemory(
            id=f"{current.memory_key}:v{current.version + 1}",
            memory_key=current.memory_key,
            tenant_id=current.tenant_id,
            project_id=current.project_id,
            owner_user_id=current.owner_user_id,
            title=str(next_title).strip(),
            body=str(next_body).strip(),
            tags=clean_tags,
            created_at=current.created_at,
            updated_at=now,
            version=current.version + 1,
            supersedes_id=current.id,
            workspace_project_id=current.workspace_project_id,
        )
        try:
            self.store.add_node(edited)
            self.store.add_edge("SUPERSEDES", edited.id, current.id, {"memory_kind": "workspace", "memory_key": current.memory_key})
        except (StoreError, TypeError, ValueError) as exc:
            return {"ok": False, "error": {"code": "MEMORY_EDIT_FAILED", "message": str(exc)}}
        return {"ok": True, "memory": self._public(edited), "updated": True}


class ProjectWorkspace:
    """Project and membership operations for the projects-first product."""

    DEFAULT_PROJECT_ID = "project:default"
    MAX_NAME = 100
    MAX_DESCRIPTION = 500
    ROLES = {"owner", "editor", "viewer"}

    def __init__(self, store: Any, auth: Any) -> None:
        self.store = store
        self.auth = auth
        self.memories = MemoryWorkspace(store)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _public_project(project: WorkspaceProject) -> dict[str, Any]:
        result = record_to_dict(project)
        result.pop("node_type", None)
        return result

    @staticmethod
    def _public_member(member: ProjectMember) -> dict[str, Any]:
        result = record_to_dict(member)
        result.pop("node_type", None)
        return result

    def _projects(self) -> list[WorkspaceProject]:
        return [item for item in self.store.nodes("WorkspaceProject") if isinstance(item, WorkspaceProject) and not item.archived]

    def _members(self, project_id: str) -> list[ProjectMember]:
        return [
            item
            for item in self.store.nodes("ProjectMember")
            if isinstance(item, ProjectMember) and item.workspace_project_id == project_id
        ]

    def ensure_default(self, owner: Identity) -> WorkspaceProject:
        existing = self.store.get_node(self.DEFAULT_PROJECT_ID)
        if isinstance(existing, WorkspaceProject):
            if not any(member.user_id == owner.user_id for member in self._members(existing.id)):
                self._add_member(existing.id, owner.user_id, "viewer")
            return existing
        now = self._now()
        project = WorkspaceProject(
            id=self.DEFAULT_PROJECT_ID,
            tenant_id=self.store.tenant_id,
            project_id=self.store.project_id,
            owner_user_id=owner.user_id,
            name="Shared memory",
            description="The starting place for team context.",
            created_at=now,
            updated_at=now,
        )
        self.store.add_node(project)
        self._add_member(project.id, owner.user_id, "owner")
        return project

    def _add_member(self, project_id: str, user_id: str, role: str) -> ProjectMember:
        member = ProjectMember(
            id=deterministic_id("project-member", project_id, user_id),
            tenant_id=self.store.tenant_id,
            project_id=self.store.project_id,
            workspace_project_id=project_id,
            user_id=user_id,
            role=role,
            created_at=self._now(),
        )
        self.store.add_node(member)
        return member

    def project(self, project_id: Any) -> WorkspaceProject | None:
        project = self.store.get_node(project_id) if isinstance(project_id, str) else None
        return project if isinstance(project, WorkspaceProject) and not project.archived else None

    def role_for(self, identity: Identity, project_id: str) -> str | None:
        project = self.project(project_id)
        if project is None:
            return None
        if project.owner_user_id == identity.user_id:
            return "owner"
        member = self.store.get_node(deterministic_id('project-member', project_id, identity.user_id))
        if not isinstance(member, ProjectMember) or member.workspace_project_id != project_id:
            return None
        return member.role if member else None

    def can_access(self, identity: Identity, project_id: str, write: bool = False) -> bool:
        role = self.role_for(identity, project_id)
        if role is None:
            return False
        return not write or role in {"owner", "editor"}

    def list_projects(self, identity: Identity) -> dict[str, Any]:
        projects = [
            project
            for project in self._projects()
            if self.role_for(identity, project.id) is not None
        ]
        result = []
        for project in sorted(projects, key=lambda item: (item.updated_at, item.id), reverse=True):
            item = self._public_project(project)
            item["role"] = self.role_for(identity, project.id)
            item["memory_count"] = len(self.memories.list_memories(project.id)["memories"])
            item["member_count"] = len(self._members(project.id))
            result.append(item)
        return {"ok": True, "projects": result, "count": len(result)}

    def create_project(self, identity: Identity, name: Any, description: Any = "") -> dict[str, Any]:
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > self.MAX_NAME:
            return {"ok": False, "error": {"code": "INVALID_PROJECT_NAME", "message": "Project name is required and must be at most 100 characters"}}
        if not isinstance(description, str) or len(description.strip()) > self.MAX_DESCRIPTION:
            return {"ok": False, "error": {"code": "INVALID_PROJECT_DESCRIPTION", "message": "Description must be at most 500 characters"}}
        now = self._now()
        project_id = f"project:{secrets.token_hex(8)}"
        project = WorkspaceProject(
            id=project_id,
            tenant_id=self.store.tenant_id,
            project_id=self.store.project_id,
            owner_user_id=identity.user_id,
            name=name.strip(),
            description=description.strip(),
            created_at=now,
            updated_at=now,
        )
        try:
            self.store.add_node(project)
            self._add_member(project.id, identity.user_id, "owner")
        except (StoreError, TypeError, ValueError) as exc:
            return {"ok": False, "error": {"code": "PROJECT_CREATE_FAILED", "message": str(exc)}}
        return {"ok": True, "project": self._public_project(project), "role": "owner"}

    def detail(self, identity: Identity, project_id: str) -> dict[str, Any]:
        project = self.project(project_id)
        role = self.role_for(identity, project_id)
        if project is None or role is None:
            return {"ok": False, "error": {"code": "PROJECT_NOT_FOUND", "message": "Project was not found"}}
        return {
            "ok": True,
            "project": {**self._public_project(project), "role": role},
            "members": [self._public_member(item) for item in self._members(project_id)],
            "memories": self.memories.list_memories(project_id)["memories"],
        }

    def add_member(self, identity: Identity, project_id: str, user_id: Any, role: Any = "editor") -> dict[str, Any]:
        if self.role_for(identity, project_id) != "owner":
            return {"ok": False, "error": {"code": "FORBIDDEN", "message": "Only the project owner can manage people"}}
        if not isinstance(user_id, str) or not any(user.user_id == user_id for user in self.auth.known_users()):
            return {"ok": False, "error": {"code": "USER_NOT_FOUND", "message": "That user is not configured in this workspace"}}
        if role not in {"editor", "viewer"}:
            return {"ok": False, "error": {"code": "INVALID_ROLE", "message": "Role must be editor or viewer"}}
        existing = next((item for item in self._members(project_id) if item.user_id == user_id), None)
        if existing:
            return {"ok": True, "member": self._public_member(existing), "idempotent": True}
        member = self._add_member(project_id, user_id, role)
        return {"ok": True, "member": self._public_member(member)}

    def graph(self, identity: Identity, project_id: str) -> dict[str, Any]:
        if not self.can_access(identity, project_id):
            return {"ok": False, "error": {"code": "PROJECT_NOT_FOUND", "message": "Project was not found"}}
        all_memories = [
            item for item in self.store.nodes("WorkspaceMemory")
            if isinstance(item, WorkspaceMemory) and item.workspace_project_id == project_id and not item.archived
        ]
        latest_by_key: dict[str, WorkspaceMemory] = {}
        for item in all_memories:
            current = latest_by_key.get(item.memory_key)
            if current is None or item.version > current.version:
                latest_by_key[item.memory_key] = item
        visible_ids = {item.id for item in latest_by_key.values()}
        nodes = []
        for item in sorted(all_memories, key=lambda value: (value.memory_key, value.version)):
            nodes.append({
                "id": item.id,
                "type": "memory",
                "title": item.title,
                "preview": item.body[:180],
                "tags": list(item.tags),
                "version": item.version,
                "current": item.id in visible_ids,
                "owner_user_id": item.owner_user_id,
                "workspace_project_id": project_id,
            })
        members = self._members(project_id)
        for member in members:
            user = next((item for item in self.auth.known_users() if item.user_id == member.user_id), None)
            nodes.append({"id": f"user:{member.user_id}", "type": "person", "name": user.display_name if user else member.user_id, "role": member.role})
        node_ids = {node["id"] for node in nodes}
        edges = []
        for edge in self.store.edges("SUPERSEDES"):
            if edge.from_id in node_ids and edge.to_id in node_ids:
                edges.append({"id": edge.id, "from": edge.from_id, "to": edge.to_id, "type": "version"})
        for item in latest_by_key.values():
            person_id = f"user:{item.owner_user_id}"
            if person_id in node_ids:
                edges.append({"id": f"author:{item.id}", "from": item.id, "to": person_id, "type": "authored_by"})
        return {"ok": True, "project": self._public_project(self.project(project_id)), "nodes": nodes, "edges": edges}
