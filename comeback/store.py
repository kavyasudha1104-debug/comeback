"""Talking to the database.

Every read and write is a call to one of the SQL functions in
database/setup.sql. There's no sign-up: each visitor gets a private guest
account (Supabase anonymous sign-in) when they press Start. Calls use the
public anon key plus that guest's token, so every call runs as that user and
the database's access rules apply. The secret key is never used.
"""

from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("comeback")
GENERIC = "Something went wrong on our side. Please try again."


class StoreError(Exception):
    """An error the user can be shown as is."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code


class ConnectionLost(StoreError):
    def __init__(self):
        super().__init__("Can't reach the server right now. Check your internet and try again.", "offline")


class AuthRequired(StoreError):
    def __init__(self, message: str = "Your session ended. Press Start to begin again."):
        super().__init__(message, "auth")


def _is_outage(code: Any) -> bool:
    """Database unreachable or restarting: PostgREST PGRST000-003, or SQLSTATE
    classes 08 (connection), 53 (resources), 57 (operator intervention)."""
    code = str(code or "")
    return code.startswith("PGRST00") or code[:2] in ("08", "53", "57")


class BaseStore:
    """Every call the app makes. Subclasses only provide _call() and start()."""

    signed_in: bool

    def _call(self, fn: str, params: dict | None = None, rows: bool = False) -> Any:
        raise NotImplementedError

    def server_today(self) -> str:
        return self._call("server_today")

    def my_profile(self) -> dict | None:
        return self._call("my_profile")

    def save_profile(self, name: str, exam_date: str, revision_days: int, units_per_day: float,
                     days_per_week: int, share: float) -> dict:
        return self._call("save_profile", {"p_name": name, "p_exam_date": exam_date,
                                           "p_revision_days": revision_days, "p_units_per_day": units_per_day,
                                           "p_days_per_week": days_per_week, "p_share": share})

    def my_state(self, days: int = 120) -> dict:
        return self._call("my_state", {"p_days": days})

    def set_done(self, subject: str, done: int, version: int | None = None) -> dict:
        return self._call("set_done", {"p_subject": subject, "p_done": done, "p_version": version})

    def log_units(self, subject: str, units: int) -> dict:
        return self._call("log_units", {"p_subject": subject, "p_units": units})

    def undo_log(self, log_id: int) -> None:
        self._call("undo_log", {"p_id": log_id})

    def set_habit(self, habit: str, done: bool) -> None:
        self._call("set_habit", {"p_habit": habit, "p_done": done})

    def set_priority(self, subject: str, priority: str, version: int | None = None) -> dict:
        return self._call("set_priority", {"p_subject": subject, "p_priority": priority, "p_version": version})

    def restore_subject(self, subject: str) -> dict:
        return self._call("restore_subject", {"p_subject": subject})

    def apply_plan(self, payload: dict) -> str:
        return self._call("apply_plan", {"p_plan": payload})

    def rate_plan(self, plan_id: str, doable: int) -> None:
        self._call("rate_plan", {"p_id": plan_id, "p_doable": doable})

    def load_sample(self) -> None:
        self._call("load_sample")

    def reset_progress(self) -> None:
        self._call("reset_progress")

    def log_event(self, name: str, props: dict | None = None) -> None:
        """Analytics must never break the app."""
        try:
            self._call("log_event", {"p_name": name, "p_props": props or {}})
        except StoreError as e:
            log.info("event %s not logged: %s", name, e.message)

    def export_my_data(self) -> dict:
        return self._call("export_my_data")

    def delete_my_data(self) -> None:
        self._call("delete_my_data")


# ---------------------------------------------------------------------------
# Supabase (the deployed app)
# ---------------------------------------------------------------------------

class SupabaseStore(BaseStore):
    def __init__(self, url: str, anon_key: str):
        from supabase import ClientOptions, create_client

        if not url or not anon_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set.")
        # One client per browser session (see ui.store()), so one user's token
        # can never end up on another user's request.
        self._client = create_client(url, anon_key, options=ClientOptions(
            auto_refresh_token=False,     # refreshed on demand in _fresh(); no background thread per visitor
            persist_session=True,         # kept in memory inside this client object only
            postgrest_client_timeout=10,
        ))
        if anon_key.startswith("sb_publishable_"):
            # New-style publishable keys aren't JWTs, so they must only go in the
            # apikey header. The Python client also sends the key as a Bearer token,
            # which Supabase rejects ("Invalid API key"). The user's own token
            # replaces this header after sign-in.
            self._client.auth._headers.pop("Authorization", None)
            self._client.options.headers.pop("Authorization", None)
        self.user_id: str | None = None

    @property
    def signed_in(self) -> bool:
        return self.user_id is not None

    def start(self) -> None:
        """Make a private guest account for this visitor. No email or password.
        Needs "Allow anonymous sign-ins" on in Supabase (Authentication -> Sign In / Providers)."""
        from supabase_auth.errors import AuthApiError, AuthRetryableError

        try:
            res = self._client.auth.sign_in_anonymously()
        except AuthRetryableError:
            raise ConnectionLost()
        except AuthApiError as e:
            raw = getattr(e, "message", "") or str(e)
            msg, code = raw.lower(), str(getattr(e, "code", "") or "")
            log.warning("anonymous sign-in failed: %s (%s)", raw, code)
            if "anonymous" in msg or "anonymous" in code:
                raise StoreError("Supabase isn't allowing guests yet. In Supabase, open Authentication -> "
                                 "Sign In / Providers, turn on 'Allow anonymous sign-ins', and click Save.")
            if "signup" in msg.replace(" ", "").replace("-", "") or "signup" in code:
                raise StoreError("Supabase isn't allowing new users. In Supabase, open Authentication -> "
                                 "Sign In / Providers, turn on 'Allow new users to sign up', and click Save.")
            if "captcha" in msg:
                raise StoreError("Supabase has CAPTCHA turned on. Turn it off under Authentication -> "
                                 "Attack Protection.")
            if "rate limit" in msg or "too many" in msg:
                raise StoreError("Too many new visitors right now. Wait a minute and try again.")
            raise StoreError(f"Couldn't start: {raw}")
        except Exception as e:
            raise _network(e)
        self.user_id = str(res.user.id) if res and res.user else None
        if not self.user_id or not res.session:
            raise StoreError("Couldn't start: Supabase didn't return a session. Check that "
                             "'Allow anonymous sign-ins' is on and 'Confirm email' isn't blocking new users.")

    def sign_out(self) -> None:
        try:
            self._client.auth.sign_out()
        except Exception:
            pass
        self.user_id = None

    def _fresh(self) -> None:
        s = self._client.auth.get_session()
        if s is None:
            self.user_id = None
            raise AuthRequired()
        if s.expires_at and s.expires_at - time.time() < 120:
            try:
                self._client.auth.refresh_session()
            except Exception:
                self.user_id = None
                raise AuthRequired()

    def _call(self, fn: str, params: dict | None = None, rows: bool = False) -> Any:
        from postgrest.exceptions import APIError

        for attempt in (1, 2):
            try:
                self._fresh()
                return self._client.rpc(fn, params or {}).execute().data
            except APIError as e:
                if e.code == "P0001":                       # raised by our own functions
                    if e.hint == "auth":
                        raise AuthRequired(e.message)
                    raise StoreError(e.message, e.hint)
                if _is_outage(e.code):
                    log.warning("%s: database unavailable (%s)", fn, e.code)
                    raise ConnectionLost()
                if e.code in ("PGRST301", "PGRST303") and attempt == 1:   # token expired mid-flight
                    try:
                        self._client.auth.refresh_session()
                        continue
                    except Exception:
                        raise AuthRequired()
                log.error("%s failed: %s %s", fn, e.code, e.message)
                raise StoreError(GENERIC, "server")
            except StoreError:
                raise
            except Exception as e:
                raise _network(e, fn)
        raise StoreError(GENERIC, "server")


def _network(e: Exception, fn: str = "auth") -> StoreError:
    import httpx

    if isinstance(e, (httpx.TransportError, ConnectionError, TimeoutError, OSError)):
        log.warning("network error in %s: %s", fn, e)
        return ConnectionLost()
    log.exception("unexpected error in %s", fn)
    return StoreError(GENERIC, "server")
