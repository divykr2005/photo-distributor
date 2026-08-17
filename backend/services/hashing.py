import numpy as np
from PIL import Image

def phash_dct(img: Image.Image) -> int:
    """
    Compute perceptual hash using DCT (Discrete Cosine Transform).
    - Convert to grayscale, resize to 32x32
    - Apply DCT-II
    - Take top-left 8x8 (excluding DC component at 0,0)
    - Compute median and threshold
    """
    from scipy.fftpack import dct
    
    img = img.convert("L").resize((32, 32), Image.Resampling.LANCZOS)
    pixels = np.asarray(img, dtype=np.float32)
    
    # 2D DCT
    dct_2d = dct(dct(pixels.T, norm='ortho').T, norm='ortho')
    
    # Top left 8x8, excluding DC (0,0)
    dctlowfreq = dct_2d[:8, :8]
    dctlowfreq_1d = dctlowfreq.flatten()[1:] 
    
    median = np.median(dctlowfreq_1d)
    
    hash_val = 0
    for i, val in enumerate(dctlowfreq_1d):
        if val > median:
            hash_val |= (1 << i)
            
    # Cast to signed 64-bit int for Postgres BIGINT
    if hash_val >= 2**63:
        hash_val -= 2**64
    return hash_val


def dhash(img: Image.Image) -> int:
    """
    Compute difference hash.
    - Convert to grayscale, resize to 9x8
    - Compare adjacent pixels in each row
    """
    img = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = np.asarray(img)
    
    hash_val = 0
    bit_idx = 0
    for row in range(8):
        for col in range(8):
            if pixels[row, col] > pixels[row, col + 1]:
                hash_val |= (1 << bit_idx)
            bit_idx += 1
            
    # Cast to signed 64-bit int for Postgres BIGINT
    if hash_val >= 2**63:
        hash_val -= 2**64
    return hash_val


def hamming(a: int, b: int) -> int:
    """Compute Hamming distance between two 64-bit integers."""
    if a is None or b is None:
        return 64
    x = np.uint64(a) ^ np.uint64(b)
    # popcount
    return x.bit_count() if hasattr(x, 'bit_count') else bin(int(x)).count('1')
