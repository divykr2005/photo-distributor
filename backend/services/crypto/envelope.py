import os
import struct
import functools
import cachetools # type: ignore
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Tuple, Dict

from .providers import get_key_provider

# In-process cache for keys to avoid constant unwrapping
# KEKs cached by event_id, DEKs by guest_id
# We use TTL cache for security and memory bounds (e.g., max 1000 items, 10 minutes)
_kek_cache: cachetools.TTLCache = cachetools.TTLCache(maxsize=1000, ttl=600)
_dek_cache: cachetools.TTLCache = cachetools.TTLCache(maxsize=10000, ttl=600)

# The master key can be cached indefinitely in process memory as it's the root of trust
@functools.lru_cache(maxsize=1)
def get_master_key() -> bytes:
    provider = get_key_provider()
    return provider.unwrap_master_key()

def purge_key_cache():
    """Explicitly purges all cached keys. Useful for testing crypto-shredding."""
    get_master_key.cache_clear()
    _kek_cache.clear()
    _dek_cache.clear()

def generate_key() -> bytes:
    """Generates a random 32-byte key."""
    return AESGCM.generate_key(bit_length=256)

def wrap_key(key_to_wrap: bytes, wrapping_key: bytes) -> Tuple[bytes, bytes]:
    """
    Wraps a key using AES-GCM.
    Returns (wrapped_key_ciphertext, nonce).
    """
    aesgcm = AESGCM(wrapping_key)
    nonce = os.urandom(12)
    wrapped = aesgcm.encrypt(nonce, key_to_wrap, None)
    return wrapped, nonce

def unwrap_key(wrapped_key: bytes, nonce: bytes, wrapping_key: bytes) -> bytes:
    """
    Unwraps a key using AES-GCM.
    Returns the original key.
    """
    aesgcm = AESGCM(wrapping_key)
    return aesgcm.decrypt(nonce, wrapped_key, None)

def get_or_unwrap_kek(event_id: str, wrapped_kek: bytes, nonce: bytes) -> bytes:
    """Unwraps and caches the KEK."""
    if event_id in _kek_cache:
        return _kek_cache[event_id]
    
    master_key = get_master_key()
    kek = unwrap_key(wrapped_kek, nonce, master_key)
    _kek_cache[event_id] = kek
    return kek

def get_or_unwrap_dek(guest_id: str, wrapped_dek: bytes, nonce: bytes, kek: bytes) -> bytes:
    """Unwraps and caches the DEK."""
    if guest_id in _dek_cache:
        return _dek_cache[guest_id]
    
    dek = unwrap_key(wrapped_dek, nonce, kek)
    _dek_cache[guest_id] = dek
    return dek

def _build_aad(guest_id: str, event_id: str, face_embedding_id: str, model_version: str) -> bytes:
    """
    Builds the Additional Authenticated Data (AAD) for embedding encryption.
    Format: {guest_id}:{event_id}:{face_embedding_id}:{model_version}
    """
    aad_str = f"{guest_id}:{event_id}:{face_embedding_id}:{model_version}"
    return aad_str.encode('utf-8')

def encrypt_embedding(
    embedding_bytes: bytes, 
    dek: bytes, 
    guest_id: str, 
    event_id: str, 
    face_embedding_id: str, 
    model_version: str
) -> Tuple[bytes, bytes]:
    """
    Encrypts the embedding bytes using AES-GCM and the DEK.
    Returns (ciphertext, nonce).
    """
    aesgcm = AESGCM(dek)
    nonce = os.urandom(12)
    aad = _build_aad(guest_id, event_id, face_embedding_id, model_version)
    ciphertext = aesgcm.encrypt(nonce, embedding_bytes, aad)
    return ciphertext, nonce

def decrypt_embedding(
    ciphertext: bytes, 
    nonce: bytes, 
    dek: bytes, 
    guest_id: str, 
    event_id: str, 
    face_embedding_id: str, 
    model_version: str
) -> bytes:
    """
    Decrypts the embedding ciphertext using AES-GCM and the DEK.
    """
    aesgcm = AESGCM(dek)
    aad = _build_aad(guest_id, event_id, face_embedding_id, model_version)
    return aesgcm.decrypt(nonce, ciphertext, aad)
