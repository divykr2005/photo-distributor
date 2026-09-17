from pydantic import BaseModel, EmailStr, Field


class EmailOtpRequest(BaseModel):
    email: EmailStr


class EmailOtpVerify(BaseModel):
    email: EmailStr
    code: str = Field(..., pattern=r"^\d{6}$")


class EmailOtpVerified(BaseModel):
    verification_token: str

