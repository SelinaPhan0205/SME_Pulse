from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from app.modules.auth.dependencies import requires_roles


def _build_user(role_codes):
    return SimpleNamespace(
        email="tester@sme.local",
        roles=[SimpleNamespace(role=SimpleNamespace(code=code)) for code in role_codes],
    )


@pytest.mark.anyio
async def test_requires_roles_allows_authorized_user():
    checker = requires_roles(["owner", "admin"])
    current_user = _build_user(["owner"])

    resolved_user = await checker(current_user=current_user)

    assert resolved_user is current_user


@pytest.mark.anyio
async def test_requires_roles_rejects_unauthorized_user():
    checker = requires_roles(["owner", "admin"])
    current_user = _build_user(["cashier"])

    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=current_user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
