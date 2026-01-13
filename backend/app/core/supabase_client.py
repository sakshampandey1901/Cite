"""Supabase client configuration for authentication."""
from supabase import create_client, Client
from app.core.config import settings


def get_supabase_client() -> Client:
    """
    Create and return Supabase client instance.

    Returns:
        Configured Supabase client
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


# Global client instance
supabase: Client = get_supabase_client()
