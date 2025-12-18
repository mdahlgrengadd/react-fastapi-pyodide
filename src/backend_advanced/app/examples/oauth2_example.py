"""
OAuth2 Authentication Example for Pyodide FastAPI Bridge

This example demonstrates how to use OAuth2 with JWT tokens in a Pyodide environment.
The bridge now supports:
- OAuth2PasswordBearer (extracts tokens from Authorization headers)
- OAuth2PasswordRequestForm (handles form-urlencoded login data)
- Full FastAPI authentication patterns
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel

# Configuration
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# In-memory user database (for demo purposes)
# In production, use a real database with hashed passwords
fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "fakehashedsecret",  # In reality, use proper password hashing
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderland",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": False,
    },
}


# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


# OAuth2 scheme - extracts token from Authorization: Bearer <token> header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(
    title="OAuth2 Authentication Demo",
    description="Demonstrates OAuth2 + JWT authentication in Pyodide",
    version="1.0.0"
)


# Utility functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Note: This is a simple comparison for demo purposes.
    In production, use proper password hashing libraries like:
    - bcrypt
    - argon2
    - pwdlib (if available in Pyodide)
    """
    # For demo: just compare directly (NEVER do this in production!)
    return plain_password == hashed_password


def get_user(db: dict, username: str) -> UserInDB | None:
    """Get user from database."""
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(fake_db: dict, username: str, password: str) -> UserInDB | bool:
    """Authenticate a user."""
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Dependency functions
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    Get the current user from the JWT token.

    This dependency uses OAuth2PasswordBearer which:
    1. Extracts the token from Authorization: Bearer <token> header
    2. Returns None if no token is present
    3. The bridge now handles this automatically!
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception

    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Check if the current user is active."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """
    Login endpoint that returns a JWT token.

    This endpoint uses OAuth2PasswordRequestForm which:
    1. Expects Content-Type: application/x-www-form-urlencoded
    2. Extracts username and password from the form data
    3. The bridge now handles this automatically!

    Test with:
    - username: johndoe
    - password: fakehashedsecret

    Or:
    - username: alice
    - password: fakehashedsecret2
    """
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/users/me/", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Get the current logged-in user's information.

    This endpoint requires authentication.
    It will:
    1. Extract the token from the Authorization header
    2. Validate the token
    3. Return the user information

    To test:
    1. First call /token to get an access_token
    2. Then call this endpoint with header: Authorization: Bearer <token>
    """
    return current_user


@app.get("/users/me/items/")
async def read_own_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Get the current user's items.

    This is another protected endpoint that requires authentication.
    """
    return [
        {"item_id": "item1", "owner": current_user.username, "name": "Laptop"},
        {"item_id": "item2", "owner": current_user.username, "name": "Phone"},
        {"item_id": "item3", "owner": current_user.username, "name": "Keyboard"},
    ]


@app.get("/")
async def root():
    """Public endpoint - no authentication required."""
    return {
        "message": "OAuth2 Authentication Demo API",
        "endpoints": {
            "POST /token": "Login and get JWT token",
            "GET /users/me/": "Get current user info (protected)",
            "GET /users/me/items/": "Get current user's items (protected)",
        },
        "test_credentials": {
            "user1": {"username": "johndoe", "password": "fakehashedsecret"},
            "user2": {"username": "alice", "password": "fakehashedsecret2"},
        }
    }


# Usage instructions
"""
HOW TO USE THIS API:

1. LOGIN (Get Token):
   POST /token
   Content-Type: application/x-www-form-urlencoded
   Body: username=johndoe&password=fakehashedsecret

   Response:
   {
     "access_token": "eyJhbGc...",
     "token_type": "bearer"
   }

2. ACCESS PROTECTED ENDPOINTS:
   GET /users/me/
   Authorization: Bearer eyJhbGc...

   Response:
   {
     "username": "johndoe",
     "email": "johndoe@example.com",
     "full_name": "John Doe",
     "disabled": false
   }

3. THE BRIDGE AUTOMATICALLY HANDLES:
   - Extracting tokens from Authorization headers
   - Parsing form-urlencoded data
   - Converting between JavaScript and Python types
   - OAuth2 security schemes
"""
