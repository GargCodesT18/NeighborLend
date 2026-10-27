"""Temporary auth/db probe. Prints no secrets."""
import json
import urllib.error
import urllib.request

from sqlalchemy import inspect, text

from app.database import engine


def post(path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        "http://localhost:8000" + path,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
            print("POST", path, resp.status)
            try:
                data = json.loads(raw)
            except Exception:
                print(raw[:500])
                return None
            if "access_token" in data:
                token = data["access_token"]
                print("token_prefix", token[:12], "len", len(token))
                print("user_keys", sorted((data.get("user") or {}).keys()))
            else:
                print(json.dumps(data)[:800])
            return data
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        print("POST", path, exc.code)
        print(raw[:1200])
        return None


def get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request("http://localhost:8000" + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
            print("GET", path, resp.status, raw[:400])
    except urllib.error.HTTPError as exc:
        print("GET", path, exc.code, exc.read().decode()[:800])


print("--- schema ---")
insp = inspect(engine)
print("users_columns", [c["name"] for c in insp.get_columns("users")])
with engine.connect() as conn:
    row = conn.execute(text(
        "SELECT id, username, email, "
        "pg_typeof(id)::text, length(password_hash), left(password_hash, 4) "
        "FROM users LIMIT 3"
    )).fetchall()
    for r in row:
        print("user_row", r[1], r[2], "id_type", r[3], "hash_len", r[4], "hash_prefix", r[5])

print("--- frontend-shaped signup ---")
post("/api/auth/register", {
    "username": "probeuser1",
    "email": "probe1@example.com",
    "password": "secret123",
    "full_name": "Probe User",
})

print("--- schema-shaped signup missing captcha ---")
post("/api/auth/register", {
    "name": "Probe User",
    "username": "probeuser2",
    "email": "probe2@example.com",
    "password": "secret123",
})
