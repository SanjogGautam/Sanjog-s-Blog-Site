from fastapi import APIRouter
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from schema import token, user_private, user_create
from sqlalchemy import select, func
import models
from database import get_db
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from config import settings
from auth import create_access_token, hash_password, verify_password, CurrentUser
#for reset logic 
from fastapi import BackgroundTasks
from datetime import UTC,datetime
from sqlalchemy import delete as sql_delete,func
from auth import generate_reset_token,hash_reset_token
from email_utils import send_password_reset_email
from schema import ChangePasswordRequest,ForgotPasswordRequest,ResetPasswordRequest

from logging_config import setup_logging
setup_logging()

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


# ── REGISTER ──────────────────────────────────
@router.post("/register", response_model=user_private, status_code=status.HTTP_201_CREATED)
async def register(user: user_create, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(func.lower(models.User.username) == user.username.lower())
    )
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username already exists")

    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == user.email.lower())
    )
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email already exists")

    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"New user registered: id={new_user.id}, username={new_user.username}")  # ✅
    return new_user


# ── LOGIN ─────────────────────────────────────
@router.post("/token", response_model=token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    email = form_data.username
    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == email.lower())
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        logger.warning(f"Failed login attempt for email={email.lower()}")  # ✅
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    logger.info(f"User logged in: id={user.id}")  # ✅
    return token(access_token=access_token, token_type="bearer")

# ── CURRENT USER ──────────────────────────────
@router.get("/me", response_model=user_private)
async def get_current_user(
    current_user: CurrentUser
):
    return current_user

@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == request_data.email.lower())
    )
    user = result.scalars().first()

    if user:
        await db.execute(
            sql_delete(models.PasswordResetToken).where(models.PasswordResetToken.user_id == user.id)
        )
        token = generate_reset_token()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.reset_token_expire_minutes)

        reset_token = models.PasswordResetToken(
            user_id=user.id, token_hash=token_hash, expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()

        background_tasks.add_task(
            send_password_reset_email, email_to=user.email, username=user.username, token=token,
        )
        logger.info(f"Password reset token generated for user_id={user.id}")  # ✅
    else:
        logger.info("Password reset requested for an email with no matching account")  # ✅ — no email/id logged, by design

    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    token_hash = hash_reset_token(request_data.token)
    result = await db.execute(
        select(models.PasswordResetToken).where(
            models.PasswordResetToken.token_hash == token_hash,
            models.PasswordResetToken.expires_at > datetime.now(UTC),
        )
    )
    reset_token = result.scalars().first()

    if not reset_token:
        logger.warning("Password reset attempted with invalid or expired token")  # ✅
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset link. Please request a new one.")

    result = await db.execute(select(models.User).where(models.User.id == reset_token.user_id))
    user = result.scalars().first()

    if not user:
        logger.warning(f"Password reset token valid but user_id={reset_token.user_id} no longer exists")  # ✅
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset link. Please request a new one.")

    user.password_hash = hash_password(request_data.new_password)
    await db.delete(reset_token)
    await db.commit()

    logger.info(f"Password successfully reset for user_id={user.id}") 
    return {"message": "Your password has been reset successfully. You can now log in."}


@router.patch("/me/change-password", status_code=status.HTTP_200_OK)  
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        logger.warning(f"Failed change-password attempt for user_id={current_user.id} — wrong current password")  # ✅
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")

    current_user.password_hash = hash_password(password_data.new_password)
    await db.commit()

    logger.info(f"Password changed for user_id={current_user.id}")  
    return {"message": "Password changed successfully."}