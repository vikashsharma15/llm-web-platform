import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from models.user import UserRole


class RegisterRequest(BaseModel):
    email:    EmailStr
    username: str
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 20:
            raise ValueError("Username must be at most 20 characters")
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("Username must contain only letters, numbers and underscores")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:  # bcrypt DoS prevention
            raise ValueError("Password must be at most 128 characters")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class OTPRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp:   str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    """Full token response on login — access + refresh."""
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int  # seconds until access token expires


class AccessTokenResponse(BaseModel):
    """Token response on refresh — new access + new refresh."""
    access_token:  str
    refresh_token: str  # rotation — new refresh token every time
    token_type:    str = "bearer"
    expires_in:    int


class UserResponse(BaseModel):
    """User data — password always excluded."""
    id:        int
    email:     str
    username:  str
    role:      str
    is_active: bool

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    message: str
    email:   str