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

router = APIRouter()


# ── REGISTER ──────────────────────────────────
@router.post("/register", response_model=user_private, status_code=status.HTTP_201_CREATED)
async def register(user: user_create, db: Annotated[AsyncSession, Depends(get_db)]):
    # check username not taken
    result = await db.execute(
        select(models.User).where(func.lower(models.User.username) == user.username.lower())
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username already exists",
        )

    # check email not taken
    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == user.email.lower())
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email already exists",
        )

    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


# ── LOGIN ─────────────────────────────────────
@router.post("/token", response_model=token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # OAuth2PasswordRequestForm always names the field "username" — we treat it as email
    email = form_data.username

    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == email.lower())
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
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
    db: Annotated[AsyncSession,Depends(get_db)],
):
    result=await db.execute(
        select(models.User).where(func.lower(models.User.email) == request_data.email.lower(),
                                  ),
    )
    user = result.scalars().first()
    if user: 
        await db.execute(
            sql_delete(models.PasswordResetToken).where(
                models.PasswordResetToken.user_id == user.id,
            ),
        )
        token = generate_reset_token()
        token_hash=hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes= settings.reset_token_expire_minutes
        )
        reset_token = models.PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()

        background_tasks.add_task(
            send_password_reset_email,
            email_to=user.email,
            username=user.username,
            token=token,
        )
    return {"message":"If an account with that email exists, a password reset link has been sent."}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # 1. Hash the incoming token so we can compare it against what's stored
    token_hash = hash_reset_token(request_data.token)

    # 2. Look up a matching, not-yet-expired reset token
    result = await db.execute(
        select(models.PasswordResetToken).where(
            models.PasswordResetToken.token_hash == token_hash,
            models.PasswordResetToken.expires_at > datetime.now(UTC),
        )
    )
    reset_token = result.scalars().first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link. Please request a new one.",
        )

    # 3. Look up the user this token belongs to
    result = await db.execute(
        select(models.User).where(models.User.id == reset_token.user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link. Please request a new one.",
        )

    # 4. Update the password
    user.password_hash = hash_password(request_data.new_password)

    # 5. Delete the token so it can't be reused
    await db.delete(reset_token)

    await db.commit()

    return {"message": "Your password has been reset successfully. You can now log in."}

#change password to the users who are already logged in and have access token
@router.put("/me/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    current_user.password_hash = hash_password(password_data.new_password)
    await db.commit()

    return {"message": "Password changed successfully."}
        