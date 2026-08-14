import urllib.request
import time

urls = [
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=800",
    "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=800",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800",
    "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800",
    "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=800",
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800",
    "https://images.unsplash.com/photo-1511632765486-a01980e01a18?w=800",
    "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=800",
    "https://images.unsplash.com/photo-1511795409834-ef04bbd61622?w=800"
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
success = 0
for idx, url in enumerate(urls, 1):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as res:
            data = res.read()
            print(f"[OK] Photo #{idx}: {len(data)} bytes")
            success += 1
    except Exception as e:
        print(f"[FAIL] Photo #{idx}: {e}")
    time.sleep(0.5)

print(f"\nDownloaded: {success}/{len(urls)}")
