from fastapi import HTTPException, status, Depends, APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from schema import Post_response, PostCreate, PostUpdate, PaginatedPostsResponse
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import models
from database import get_db
from auth import CurrentUser
from models import RoleName

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=Post_response, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=current_user.id,
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])

    logger.info(f"Post created: id={new_post.id}, by user_id={current_user.id}")  # ✅
    return new_post


@router.get("", response_model=PaginatedPostsResponse)
async def get_all_posts(db: Annotated[AsyncSession, Depends(get_db)],
                        skip: Annotated[int, Query(ge=0)] = 0,
                        limit: Annotated[int, Query(ge=1, le=100)] = 10):
    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar()
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
        .offset(skip)
        .limit(limit)
    )
    posts = result.scalars().all()
    has_more = skip + len(posts) < total
    return PaginatedPostsResponse(
        posts=[Post_response.model_validate(post) for post in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.get("/{post_id}", response_model=Post_response)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post is not found")
    return post


@router.put("/{post_id}", response_model=Post_response)
async def update_post_full(
    post_id: int,
    post_data: PostCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post is not found")

    is_owner = post.user_id == current_user.id
    is_privileged = bool(current_user.role_names & {RoleName.admin.value, RoleName.superadmin.value})

    if not is_owner and not is_privileged:
        logger.warning(f"Unauthorized PUT attempt on post_id={post_id} by user_id={current_user.id}")  # ✅
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update")

    if not is_owner and is_privileged:
        logger.info(f"Privileged edit: user_id={current_user.id} (role) edited post_id={post_id} owned by user_id={post.user_id}")  # ✅

    post.title = post_data.title
    post.content = post_data.content
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post Not Found")

    is_owner = post.user_id == current_user.id
    is_privileged = bool(current_user.role_names & {RoleName.admin.value, RoleName.superadmin.value})

    if not is_owner and not is_privileged:
        logger.warning(f"Unauthorized DELETE attempt on post_id={post_id} by user_id={current_user.id}")  # ✅
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update")

    if not is_owner and is_privileged:
        logger.info(f"Privileged delete: user_id={current_user.id} (role) deleted post_id={post_id} owned by user_id={post.user_id}")  # ✅
    else:
        logger.info(f"Post deleted: id={post_id}, by owner user_id={current_user.id}")  # ✅

    await db.delete(post)
    await db.commit()


@router.patch("/{post_id}", response_model=Post_response)
async def update_post_partial(
    post_id: int,
    post_data: PostUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    is_owner = post.user_id == current_user.id
    is_privileged = bool(current_user.role_names & {RoleName.admin.value, RoleName.superadmin.value})

    if not is_owner and not is_privileged:
        logger.warning(f"Unauthorized PATCH attempt on post_id={post_id} by user_id={current_user.id}")  # ✅
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update")

    if not is_owner and is_privileged:
        logger.info(f"Privileged edit: user_id={current_user.id} (role) patched post_id={post_id} owned by user_id={post.user_id}")  # ✅

    data = post_data.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=['author'])
    return post