"""
Multi-Tenant & RBAC — TIP-16

Lightweight tenant isolation and role-based access control.
For Phase 6: basic implementation, production would add JWT auth.

Tenants: each org has own projects, isolated data.
Roles: admin (full), analyst (create/run), viewer (read-only).
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("mirofish.tenant")


class Role(str, Enum):
    ADMIN = "admin"       # Full access, manage users, billing
    ANALYST = "analyst"   # Create/run simulations, view reports
    VIEWER = "viewer"     # Read-only access to reports


@dataclass
class Tenant:
    id: str
    name: str
    api_key_hash: str = ""  # hashed API key for LLM (tenant brings own)
    created_at: str = ""
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "created_at": self.created_at, "settings": self.settings}


@dataclass
class TenantUser:
    user_id: str
    tenant_id: str
    role: Role
    email: str = ""
    name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"user_id": self.user_id, "tenant_id": self.tenant_id, "role": self.role.value, "email": self.email, "name": self.name}


class TenantManager:
    """
    In-memory tenant manager (Phase 6 starter).

    Production: back with DB + JWT token extraction.
    """

    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._users: Dict[str, TenantUser] = {}
        # Default tenant for single-tenant mode
        self._tenants["default"] = Tenant(id="default", name="Default Organization")

    def create_tenant(self, tenant_id: str, name: str) -> Tenant:
        t = Tenant(id=tenant_id, name=name)
        self._tenants[tenant_id] = t
        return t

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def list_tenants(self) -> List[Dict]:
        return [t.to_dict() for t in self._tenants.values()]

    def add_user(self, user_id: str, tenant_id: str, role: Role, email: str = "", name: str = "") -> TenantUser:
        user = TenantUser(user_id=user_id, tenant_id=tenant_id, role=role, email=email, name=name)
        self._users[user_id] = user
        return user

    def get_user(self, user_id: str) -> Optional[TenantUser]:
        return self._users.get(user_id)

    def check_permission(self, user_id: str, action: str) -> bool:
        """
        Check if user has permission for an action.

        Actions: create_project, run_simulation, view_report, manage_users, export_audit
        """
        user = self._users.get(user_id)
        if not user:
            return True  # No auth configured = allow all (single-tenant mode)

        permissions = {
            Role.ADMIN: {"create_project", "run_simulation", "view_report", "manage_users", "export_audit", "delete_project"},
            Role.ANALYST: {"create_project", "run_simulation", "view_report"},
            Role.VIEWER: {"view_report"},
        }

        allowed = permissions.get(user.role, set())
        return action in allowed

    def get_tenant_for_user(self, user_id: str) -> str:
        user = self._users.get(user_id)
        return user.tenant_id if user else "default"


# Global singleton
tenant_manager = TenantManager()
