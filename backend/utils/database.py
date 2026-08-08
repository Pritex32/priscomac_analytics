import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
print("SUPABASE_SECRET_KEY exists:", bool(SUPABASE_SECRET_KEY))
print("SUPABASE_SECRET_KEY length:", len(SUPABASE_SECRET_KEY) if SUPABASE_SECRET_KEY else 0)


supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

def get_db():
    return supabase
