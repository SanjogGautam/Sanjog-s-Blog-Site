from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

import models
from models import RoleName
from database import get_db
from auth import CurrentUser

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


# ── STARTUP / SEEDING (called once from main.py's lifespan) ──────────

async def seed_roles(db: AsyncSession) -> None:
    """Ensure the three role rows exist. Safe to call on every startup."""
    created_any = False
    for role_name in RoleName:
        result = await db.execute(select(models.Role).where(models.Role.name == role_name))
        if not result.scalars().first():
            db.add(models.Role(name=role_name))
            created_any = True
    await db.commit()
    if created_any:
        logger.info("Role table seeded (one or more roles were missing and have been created)")  # ✅


async def ensure_superadmin(db: AsyncSession, email: str) -> None:
    """Guarantee the configured superadmin email always holds the superadmin role."""
    result = await db.execute(
        select(models.User).where(models.User.email == email.lower())
    )
    user = result.scalars().first()
    if not user:
        logger.warning(f"SUPERADMIN_EMAIL ({email}) does not match any existing account yet")  # ✅
        return

    result = await db.execute(
        select(models.Role).where(models.Role.name == RoleName.superadmin)
    )
    superadmin_role = result.scalars().first()

    if superadmin_role not in user.roles:
        user.roles.append(superadmin_role)
        await db.commit()
        logger.info(f"Superadmin role attached to user_id={user.id} ({user.username})")  # ✅


# ── PERMISSION DEPENDENCIES (used by other routers to protect routes) ─

def require_role(*allowed_roles: RoleName):
    """
    Returns a FastAPI dependency that only allows users holding at least
    one of the given roles. Usage: Depends(require_role(RoleName.admin, RoleName.superadmin))
    """
    async def checker(current_user: CurrentUser) -> models.User:
        allowed_names = {r.value for r in allowed_roles}
        if not (current_user.role_names & allowed_names):
            logger.warning(
                f"Permission denied: user_id={current_user.id} (roles={current_user.role_names}) "
                f"attempted an action requiring one of {allowed_names}"
            )  # ✅
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to perform this action.",
            )
        return current_user
    return checker


# ── ENDPOINTS ──────────────────────────────────────────────────────

@router.get("/roles", response_model=list[str])
async def list_available_roles(
    current_user: Annotated[models.User, Depends(require_role(RoleName.admin, RoleName.superadmin))],
):
    return [role.value for role in RoleName]


@router.patch("/users/{user_id}/promote", status_code=status.HTTP_200_OK)
async def promote_user(
    user_id: int,
    current_user: Annotated[models.User, Depends(require_role(RoleName.superadmin))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    target_user = result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_user.has_role(RoleName.superadmin):
        logger.warning(f"superadmin user_id={current_user.id} attempted to modify the superadmin's own role")  # ✅
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify the superadmin's role.")

    if target_user.has_role(RoleName.admin):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already an admin.")

    result = await db.execute(select(models.Role).where(models.Role.name == RoleName.admin))
    admin_role = result.scalars().first()
    target_user.roles.append(admin_role)
    await db.commit()
    await db.refresh(target_user)

    logger.info(
        f"ROLE CHANGE: user_id={current_user.id} promoted user_id={target_user.id} "
        f"({target_user.username}) to admin"
    )  # ✅
    return {"message": f"{target_user.username} has been promoted to admin."}


@router.patch("/users/{user_id}/demote", status_code=status.HTTP_200_OK)
async def demote_user(
    user_id: int,
    current_user: Annotated[models.User, Depends(require_role(RoleName.superadmin))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    target_user = result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_user.has_role(RoleName.superadmin):
        logger.warning(f"superadmin user_id={current_user.id} attempted to modify the superadmin's own role")  # ✅
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify the superadmin's role.")

    result = await db.execute(select(models.Role).where(models.Role.name == RoleName.admin))
    admin_role = result.scalars().first()

    if admin_role not in target_user.roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not currently an admin.")

    target_user.roles.remove(admin_role)
    await db.commit()
    await db.refresh(target_user)

    logger.info(
        f"ROLE CHANGE: user_id={current_user.id} demoted user_id={target_user.id} "
        f"({target_user.username}) from admin"
    )  # ✅
    return {"message": f"{target_user.username} has been demoted to a regular user."}