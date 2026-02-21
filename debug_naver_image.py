import requests

image_url = "https://lh3.googleusercontent.com/J6_coFbogxhRI9iM864NL_liGXvsQp2AupsKei7z0cNNfDvGUmWUy20nuUhkREQyrpY4bEeIBuc=s0-w300-rw"

print(f"Original Image URL: {image_url}")

# Try high-res variants
variants = [
    image_url.replace("=s0-w300-rw", "=s0-w1000-rw"), # Higher width
    image_url.replace("=s0-w300-rw", "=s0"),          # Original size?
    image_url.split("=")[0]                           # No params
]

for v in variants:
    print(f"\nTesting Variant: {v}")
    try:
        r = requests.head(v, timeout=5)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print(f"Content-Length: {r.headers.get('content-length', 'unknown')}")
            print(f"Content-Type: {r.headers.get('content-type', 'unknown')}")
    except Exception as e:
        print(f"Error: {e}")
