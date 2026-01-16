"""Supabase client configuration for authentication."""
import logging
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global client instance (lazy-loaded)
_supabase_client: Client = None


def get_supabase_client() -> Client:
    """
    Create and return Supabase client instance with error handling.
    
    Returns:
        Configured Supabase client
        
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not configured
        Exception: If client creation fails
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    # Validate configuration
    if not settings.SUPABASE_URL:
        raise ValueError(
            "SUPABASE_URL is not configured. "
            "Set it in your .env file or environment variables."
        )
    
    if not settings.SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_KEY is not configured. "
            "Set it in your .env file or environment variables."
        )
    
    try:
        # Create client with timeout configuration
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
            options=ClientOptions(
                auto_refresh_token=True,
                persist_session=True,
            )
        )
        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        raise ValueError(
            f"Failed to initialize Supabase client: {str(e)}\n"
            "Please verify:\n"
            "1. SUPABASE_URL is correct (format: https://{project-ref}.supabase.co)\n"
            "2. SUPABASE_KEY is correct (anon/public key from Supabase dashboard)\n"
            "3. Network connectivity to Supabase"
        ) from e


# Lazy initialization - only create when first accessed
def get_supabase() -> Client:
    """Get Supabase client (alias for get_supabase_client)."""
    return get_supabase_client()


# For backward compatibility, try to initialize on import (but handle errors gracefully)
try:
    supabase: Client = get_supabase_client()
except Exception as e:
    logger.warning(f"Supabase client not initialized on import: {e}")
    logger.warning("Client will be initialized on first use")
    supabase = None
