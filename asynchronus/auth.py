from datetime import UTC,datetime,timedelta
import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from config import settings
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import models
from database import get_db
import hashlib 
import secrets
passowrd_hash=PasswordHash.recommended()#to hash the password(creates password hasher with argon 2 with recommended settings)
oauth2_scheme=OAuth2PasswordBearer(tokenUrl="api/auth/token")#OAuth2PasswordBearer extracts the token from the Authorization header and verifies the format of the token and returns the token if valid otherwise raises an error
def hash_password(password:str):
    return passowrd_hash.hash(password)
def verify_password(plain_password:str,hashed_password:str):
    return passowrd_hash.verify(plain_password,hashed_password)

def generate_reset_token()-> str:
    return secrets.token_urlsafe(32)# this function creates urlbase64 char which is perfect for email links
def hash_reset_token(token: str)-> str:
    return hashlib.sha256(token.encode()).hexdigest()# takes a token and returns its sha-256 hash

#to create access token
def create_access_token(data:dict,expires_delta:timedelta|None=None):
    to_encode=data.copy()
    if expires_delta:
        expire=datetime.now(tz=UTC)+expires_delta
    else:
        expire=datetime.now(tz=UTC)+timedelta(minutes=15)
    to_encode.update({"exp":expire})
    encoded_jwt=jwt.encode(to_encode,settings.secret_key.get_secret_value(),algorithm=settings.algorithm)
    return encoded_jwt
#to verify the access tokens
def verify_access_token(token:str):
    """Verifies the access tokens and returns the subject(user id) if valid"""
    try: 
        payload=jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require":['exp','sub']},
            )
    except jwt.InvalidTokenError:
        return None
    else:
        return payload.get("sub")
    
async def get_current_user(
    auth_token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    user_id = verify_access_token(auth_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try: 
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired ",
            headers={"WWW-Authenticate": "Bearer"},
        )


    result = await db.execute(select(models.User).where(models.User.id == user_id_int))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
CurrentUser=Annotated[models.User,Depends(get_current_user)]
"""
JWT has 3 parts: header, payload and signature
header: contains the type of the token and the algorithm used to sign the token
payload: contains the claims (data) of the token
signature: is used to verify the authenticity of the token and is created by signing the header and payload with the secret key using the specified algorithm
all 3 are base64 encoded and concatenated with dots to form the final token
"""