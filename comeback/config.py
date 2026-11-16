"""Reads SUPABASE_URL and SUPABASE_ANON_KEY from .streamlit/secrets.toml
(or environment variables)."""

from __future__ import annotations

import base64
import json
import os


def _get(name: str) -> str | None:
    v = os.environ.get(name)
    if v:
        return v
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None


def _jwt_role(key: str) -> str | None:
    try:
        payload = key.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("role")
    except Exception:
        return None


def check_public_key(key: str) -> None:
    """Refuse to run with a key that bypasses the database's access rules."""
    if key.startswith("sb_secret_") or _jwt_role(key) == "service_role":
        raise RuntimeError(
            "SUPABASE_ANON_KEY is a secret/service-role key. That key ignores every access rule, "
            "so the app refuses to use it. Use the anon or publishable key.")


def make_store():
    from .store import SupabaseStore

    url, key = _get("SUPABASE_URL"), _get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_ANON_KEY (see docs/tech.md).")
    check_public_key(key)
    return SupabaseStore(url, key)
