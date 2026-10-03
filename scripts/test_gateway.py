import urllib.request
import urllib.error

req = urllib.request.Request('https://gateway.yamlr.dev/v1/sync/entitlements?machine_id=TEST-1234', headers={'User-Agent': 'Mozilla/5.0'})
try:
    response = urllib.request.urlopen(req)
    print("Success:")
    print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"Error {e.code}:")
    print(e.read().decode())
