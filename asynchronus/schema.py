from pydantic import BaseModel, Field, ConfigDict, EmailStr,field_validator
from datetime import datetime

# 1. The Shared Blueprint (Fields common to both creating and reading data)
class userBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    email: EmailStr = Field(...,max_length=120)

# 2. The Input Schema (What the server expects when a user registers)
class user_create(userBase):
    password:str = Field(..., min_length=6, max_length=128)


# 3. The Output Schema (What the server sends safely back to the browser)
class user_public(BaseModel):
    # Allows Pydantic to read database object attributes directly
    model_config = ConfigDict(from_attributes=True)
    id : int
    username: str
    image_file: str | None
    image_path: str
    roles: list[str] = []
    @field_validator("roles", mode="before")
    @classmethod
    def extract_role_names(cls, v):
        if v and hasattr(v[0], "name"):
            return [role.name.value for role in v]
        return v
class user_private(userBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: EmailStr
    image_file: str | None
    image_path: str
    roles: list[str] = []
    @field_validator("roles", mode="before")
    @classmethod
    def extract_role_names(cls, v):
        if v and hasattr(v[0], "name"):
            return [role.name.value for role in v]
        return v
class UserUpdate(BaseModel):
    username: str|None = Field(default=None,min_length=3, max_length=40)
    email: EmailStr|None = Field(default=None,max_length=120)
class token(BaseModel):
    access_token: str
    token_type: str 

class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)
class PostCreate(PostBase):
    pass

class Post_response(PostBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    date_posted:datetime
    author: user_public 
class PaginatedPostsResponse(BaseModel):
    posts: list[Post_response]
    total: int
    skip: int
    limit: int
    has_more: bool
class PostUpdate(BaseModel):
    title: str|None = Field(default=None,min_length=1, max_length=50)
    content: str|None = Field(default=None,min_length=1)
class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(max_length=120)
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)
class ChangePasswordRequest(BaseModel):
    current_password : str 
    new_password: str = Field(min_length=8)