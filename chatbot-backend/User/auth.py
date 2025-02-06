
from fastapi import HTTPException
from backend.supabase_client import supabase
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


SECRET_KEY = "your-secret-key"  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30



def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)



def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt



def register_user(first_name: str, last_name: str, email: str, password: str):
    try:
        existing_user = supabase.table('users').select('*').eq('email', email).execute()
        if existing_user.data:
            raise HTTPException(status_code=400, detail="Email is already registered")
        
        hashed_password = hash_password(password)

       
       
        user = supabase.table('users').insert({
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': hashed_password
        }).execute()

        if user_response.status_code == 201:
            new_user = user_response.data[0]
            return {"message": "User registered successfully", "user": new_user}
        else:
            raise HTTPException(status_code=400, detail="Failed to register user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def login_user(email: str, password: str):
    try:
        
        
        user = supabase.table('users').select('*').eq('email', email).execute()

        if not user.data:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user.data[0]

        if not verify_password(password, user_data['password']):
            raise HTTPException(status_code=400, detail="Invalid password")


        access_token = create_access_token(data={"sub": user_data['email'], "user_id": user_data['id']})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
