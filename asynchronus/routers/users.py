from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from schema import user_public, user_private
from typing import Annotated
from schema import Post_response, UserUpdate, PaginatedPostsResponse
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import models
from database import get_db
from auth import CurrentUser
from PIL import UnidentifiedImageError
from starlette.concurrency import run_in_threadpool
from image_utils import delete_profile_image, process_profile_image
from config import settings
from routers.rbac import require_role
from models import RoleName

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[user_public])
async def get_all_users(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User))
    user = result.scalars().all()
    return user


@router.get("/{user_id}", response_model=user_public)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


# ── user delete ──
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_self = user_id == current_user.id
    is_privileged = bool(current_user.role_names & {RoleName.admin.value, RoleName.superadmin.value})

    if not is_self and not is_privileged:
        logger.warning(f"Unauthorized DELETE attempt on user_id={user_id} by user_id={current_user.id}")  # ✅
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user")

    if user.has_role(RoleName.superadmin):
        logger.warning(f"user_id={current_user.id} attempted to delete the superadmin account")  # ✅
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The superadmin account cannot be deleted")

    if is_privileged and not is_self:
        logger.info(f"ACCOUNT DELETED: user_id={current_user.id} (privileged) deleted user_id={user.id} ({user.username})")  # ✅
    else:
        logger.info(f"ACCOUNT DELETED: user_id={user.id} ({user.username}) deleted their own account")  # ✅

    old_filename = user.image_file
    await db.delete(user)
    await db.commit()
    if old_filename:
        delete_profile_image(old_filename)


# user patch update
@router.patch("/{user_id}", response_model=user_public)
async def user_update_parital(
    user_id: int,
    user_data: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    is_self = user_id == current_user.id
    is_privileged = bool(current_user.role_names & {RoleName.admin.value, RoleName.superadmin.value})

    if not is_self and not is_privileged:
        logger.warning(f"Unauthorized PATCH attempt on user_id={user_id} by user_id={current_user.id}")  # ✅
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user")

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_data.username is not None and user_data.username.lower() != user.username.lower():
        result = await db.execute(
            select(models.User).where(func.lower(models.User.username) == user_data.username.lower())
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username already exists")

    if user_data.email is not None and user_data.email.lower() != user.email.lower():
        result = await db.execute(
            select(models.User).where(func.lower(models.User.email) == user_data.email.lower())
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email already exists")

    if not is_self and is_privileged:
        logger.info(f"Privileged edit: user_id={current_user.id} edited account user_id={user.id} ({user.username})")  # ✅

    if user_data.email is not None:
        user.email = user_data.email
    if user_data.username is not None:
        user.username = user_data.username

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{user_id}/posts", response_model=PaginatedPostsResponse)
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)],
                         limit: Annotated[int, Query(ge=0, le=100)] = 10,
                         skip: Annotated[int, Query(ge=0)] = 0):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not Found")
    count_result = await db.execute(
        select(func.count()).select_from(models.Post).where(models.Post.user_id == user_id)
    )
    total = count_result.scalar() or 0
    result = await db.execute(select(models.Post)
                              .options(selectinload(models.Post.author))
                              .where(models.Post.user_id == user_id)
                              .order_by(models.Post.date_posted.desc())
                              .offset(skip)
                              .limit(limit))
    posts = result.scalars().all()
    has_more = len(posts) < total
    return PaginatedPostsResponse(
        posts=[Post_response.model_validate(post) for post in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.patch("/{user_id}/picture", response_model=user_private)
async def upload_profile_picture(
    user_id: int,
    file: UploadFile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.id != user_id:
        logger.warning(f"Unauthorized picture upload attempt on user_id={user_id} by user_id={current_user.id}")  # ✅
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update thsi profile picture")

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File to large. Maximum size of the file is {settings.max_upload_size_bytes//(1024*1024)}MB"
        )
    try:
        new_filename = await run_in_threadpool(process_profile_image, content)
    except UnidentifiedImageError as err:
        logger.warning(f"user_id={current_user.id} uploaded an unprocessable image file")  # ✅
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file upload (Jpeg or png)") from err

    old_filename = current_user.image_file
    current_user.image_file = new_filename
    await db.commit()
    await db.refresh(current_user)
    if old_filename:
        delete_profile_image(old_filename)

    logger.info(f"Profile picture updated for user_id={current_user.id}")  # ✅
    return current_user


@router.delete("/{user_id}/picture", response_model=user_private)
async def delete_profile_picture(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if current_user.id != user_id:
        logger.warning(f"Unauthorized picture delete attempt on user_id={user_id} by user_id={current_user.id}")  # ✅
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't delete this profile picture")

    old_filename = current_user.image_file
    if old_filename is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    current_user.image_file = None
    await db.commit()
    await db.refresh(current_user)
    delete_profile_image(old_filename)

    logger.info(f"Profile picture removed for user_id={current_user.id}")  
    return current_user