
from fastapi import HTTPException, Depends
from backend.supabase_client import supabase
from backend.auth import create_access_token
from fastapi.security import OAuth2PasswordBearer


def get_profile(user_id):
    try:
        user = supabase.table('users').select('*').eq('id', user_id).execute()
        if not user.data:
            raise HTTPException(status_code=404, detail="User not found")
        return user.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def update_profile(user_id, first_name: str = None, last_name: str = None, phone_number: str = None, birth_date: str = None):
    try:
        update_data = {}
        if first_name:
            update_data['first_name'] = first_name
        if last_name:
            update_data['last_name'] = last_name
        if phone_number:
            update_data['phone_number'] = phone_number
        if birth_date:
            update_data['birth_date'] = birth_date

        if update_data:
            user = supabase.table('users').update(update_data).eq('id', user_id).execute()
            if user.status_code == 200:
                return {"message": "Profile updated successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update profile")
        else:
            return {"error": "No data to update"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
