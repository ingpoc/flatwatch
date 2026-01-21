# Tests for RBAC functionality
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Get admin token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@flatwatch.test", "password": "any"},
    )
    return response.json()["access_token"]


@pytest.fixture
def resident_token(client):
    """Get resident token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "resident@flatwatch.test", "password": "any"},
    )
    return response.json()["access_token"]


def test_admin_stats_with_admin(client, admin_token):
    """Test admin can access stats."""
    response = client.get(
        "/api/admin/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "super_admin"
    assert "stats" in data


def test_admin_stats_with_resident(client, resident_token):
    """Test resident cannot access admin stats."""
    response = client.get(
        "/api/admin/stats",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert response.status_code == 403


def test_list_users_with_admin(client, admin_token):
    """Test admin can list users."""
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert len(data["users"]) >= 2


def test_list_users_with_resident(client, resident_token):
    """Test resident cannot list users."""
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert response.status_code == 403


def test_delete_user_with_super_admin(client, admin_token):
    """Test super_admin can delete users."""
    response = client.delete(
        "/api/admin/users/999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


def test_delete_user_with_resident(client, resident_token):
    """Test resident cannot delete users."""
    response = client.delete(
        "/api/admin/users/999",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert response.status_code == 403


def test_update_role_with_super_admin(client, admin_token):
    """Test super_admin can update roles."""
    response = client.post(
        "/api/admin/roles/2",
        params={"new_role": "admin"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


def test_unauthorized_access_no_token(client):
    """Test unauthorized access without token."""
    response = client.get("/api/admin/stats")
    assert response.status_code == 401


def test_role_hierarchy():
    """Test role hierarchy."""
    from app.rbac import has_required_role

    assert has_required_role("super_admin", ["admin"])
    assert has_required_role("super_admin", ["resident"])
    assert has_required_role("admin", ["resident"])
    assert not has_required_role("resident", ["admin"])
    assert not has_required_role("resident", ["super_admin"])


def test_permissions():
    """Test role permissions."""
    from app.rbac import has_permission, Permission

    # Resident permissions
    assert has_permission("resident", Permission.VIEW_TRANSACTIONS)
    assert has_permission("resident", Permission.CREATE_CHALLENGE)
    assert not has_permission("resident", Permission.VERIFY_TRANSACTION)

    # Admin permissions
    assert has_permission("admin", Permission.VERIFY_TRANSACTION)
    assert has_permission("admin", Permission.RESOLVE_CHALLENGE)
    assert not has_permission("admin", Permission.MANAGE_USERS)

    # Super admin has all
    assert has_permission("super_admin", Permission.MANAGE_USERS)
