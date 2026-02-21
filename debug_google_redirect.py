import requests
from bs4 import BeautifulSoup

import base64

url = "https://news.google.com/rss/articles/CBMiakFVX3lxTE5rTUhKc19TTzR3emxnQm8xaVo4dl9QN3lSeDhBUFpjU0xmQktTS3E1Mk1EY3dsZU10QjN5dzFUVml4dHZtN2NsOVdkWDdtN21PXzlhV2NyN1B0SE1GOVpPdUk3QUlvQ085M2fSAW5BVV95cUxQTjRFaDNMMEVFVjU4X1NZX1BYdllXcVhrYmdwVmtXcmllVnBVRlVNZWRDWlBERkstU1MyOWk4T0hoWk9RTllpMFJ1Z1dOVjQ0bVNaWmo0eU5KUmR5eEdFZmJsTldNejV4TnpESnJ3QQ?oc=5"

# 1. Try decoding Base64
try:
    # Extract the ID part
    id_part = url.split("/articles/")[1].split("?")[0]
    # Add padding
    id_part += "=" * ((4 - len(id_part) % 4) % 4)
    decoded = base64.urlsafe_b64decode(id_part)
    print(f"Decoded Base64 (first 100 bytes): {decoded[:100]}")
    # Search for http in decoded
    if b"http" in decoded:
        import re
        urls = re.findall(b'(https?://[^\x00-\x1F]+)', decoded)
        print("Found URLs in Base64:", urls)
except Exception as e:
    print(f"Base64 Decode Error: {e}")

import re

# 2. Try Googlebot UA
headers = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
}
print(f"\nTesting URL with Googlebot UA: {url}")
try:
    r = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
    print(f"Final URL: {r.url}")
    print(f"Status Code: {r.status_code}")
    
    # Extract all URLs from text to see if the real link is hidden there
    candidates = re.findall(r'(https?://[^"\s<>\\]+)', r.text)
    print(f"Found {len(candidates)} URL candidates in text.")
    for c in candidates:
        if "google" not in c and "gstatic" not in c and "w3.org" not in c:
            print(f"Candidate: {c}")

except Exception as e:
    print(f"Request Error: {e}")
