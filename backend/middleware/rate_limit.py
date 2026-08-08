from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory rate limiting for development.
# Week 2 will add Redis as the storage backend for production.
limiter = Limiter(key_func=get_remote_address)
