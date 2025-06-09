from supabase import create_client, Client

SUPABASE_URL = "https://<your-project>.supabase.co"
SUPABASE_KEY = "<your-anon-or-service-role-key>"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
