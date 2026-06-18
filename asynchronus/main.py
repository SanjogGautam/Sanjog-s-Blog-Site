from fastapi import FastAPI, Request, HTTPException, status, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from fastapi.exception_handlers import (
    http_exception_handler, request_validation_exception_handler)
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as starletteHTTPException
from typing import Annotated
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from routers import authenticate, rbac          # rbac
import models
from database import Base, engine, get_db, session   # session
from routers import users, posts
from schema import Post_response, PaginatedPostsResponse
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # seed RBAC roles and ensure the configured superadmin holds that role
    async with session() as db:                  
        await rbac.seed_roles(db)
        await rbac.ensure_superadmin(db, settings.superadmin_email)

    yield
    # shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")
app.include_router(authenticate.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=['posts'])
app.include_router(rbac.router, prefix="/api/rbac", tags=["RBAC"])    # added


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/posts", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar() or 0
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).order_by(models.Post.date_posted.desc()).limit(settings.post_per_page))
    posts_list = result.scalars().all()
    has_more = total > len(posts_list)
    return templates.TemplateResponse(
        request, name="home.html",
        context={
            "posts_list": posts_list,
            "title": "Home",
            "limit": settings.post_per_page,
            "has_more": has_more
        }
    )


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 10,
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user is not found")

    count_result = await db.execute(
        select(func.count()).select_from(models.Post).where(models.Post.user_id == user_id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
        .offset(skip)
        .limit(limit)
    )
    posts = result.scalars().all()
    has_more = skip + len(posts) < total

    return templates.TemplateResponse(
        request, name="users_post.html",
        context={
            "posts_list": posts,
            "author": user,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": has_more,
            "title": f"{user.username}'s Posts"
        }
    )


@app.get("/posts/{post_id}", include_in_schema=False, response_model=Post_response)
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        title = post.title
        return templates.TemplateResponse(
            request, name="post.html",
            context={
                "post": post,
                "title": title
            })
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail="Post is not found")


@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        name="login.html",
        context={"title": "Login"})


@app.get("/register", include_in_schema=False)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        name="register.html",
        context={"title": "Register"})


@app.get("/account", response_class=HTMLResponse, include_in_schema=False)
async def account_page(request: Request):
    return templates.TemplateResponse(request, name="account.html", context={"title": "My Account"})


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_page(request: Request):
    return templates.TemplateResponse(request, name="admin.html", context={"title": "Admin"})


@app.get("/forgot-password", response_class=HTMLResponse, include_in_schema=False)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, name="forgot_password.html", context={"title": "Forgot Password"})


@app.get("/reset-password", response_class=HTMLResponse, include_in_schema=False)
async def reset_password_page(request: Request, token: str):
    return templates.TemplateResponse(request, name="reset_password.html", context={"title": "Reset Password", "token": token})

@app.get("/test-email", include_in_schema=False)
async def test_email():
    from email_utils import send_email
    await send_email(
        email_to="test@test.com",
        subject="Test",
        plain_text="It works.",
        html_content=None,
    )
    return {"status": "sent"}

@app.exception_handler(starletteHTTPException)
async def general_http_excetption_handler(request: Request, exception: starletteHTTPException):
    message = (exception.detail
               if exception.detail
               else "An error Occurred!")
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)
    return templates.TemplateResponse(request, name="error.html",
                                      context={
                                          "status_code": exception.status_code,
                                          "title": exception.status_code,
                                          "message": message
                                      },
                                      status_code=exception.status_code)


@app.exception_handler(RequestValidationError)
async def general_validation_excetption_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)
    return templates.TemplateResponse(request, name="error.html",
                                      context={
                                          "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
                                          "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
                                          "message": "invalid Request! check your input and try again"
                                      },
                                      status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)