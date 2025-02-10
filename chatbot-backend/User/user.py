import os
import jwt
from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext
from dotenv import load_dotenv
from database.database_utils import supabase  # Database connection via database_utils.py

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash the password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare the plain password with the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/register", tags=["User"])
async def register(user: dict):
    """
    User registration.
    Expected input:
      - first_name: First name
      - last_name: Last name
      - phone_number: Phone number
      - email: Email
      - birth_date: Birth date (as a string)
      - password: Password (plain text)
    """
    email = user.get("email")
    password = user.get("password")
    
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required."
        )
    
    # Check if a user with the same email already exists
    existing_user = supabase.table("users").select("*").eq("email", email).execute()
    if existing_user.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email is already registered."
        )
    
    hashed_password = hash_password(password)
    
    user_data = {
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "phone_number": user.get("phone_number"),
        "email": email,
        "birth_date": user.get("birth_date"),
        "password_hash": hashed_password
    }
    
    result = supabase.table("users").insert(user_data).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred during user registration."
        )
    
    return {"message": "Registration was successful."}

@router.post("/login", tags=["User"])
async def login(user: dict):
    """
    User login.
    Expected input:
      - email: Email
      - password: Password
    On success, returns a JWT token.
    """
    email = user.get("email")
    password = user.get("password")
    
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required."
        )
    
    result = supabase.table("users").select("*").eq("email", email).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    db_user = result.data[0]
    if not verify_password(password, db_user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password."
        )
    
    payload = {
        "user_id": db_user.get("id"),  # Assuming the "id" column is the unique identifier
        "email": email
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": token, "token_type": "bearer"}
