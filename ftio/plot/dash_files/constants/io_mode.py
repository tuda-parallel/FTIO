"""Input/output modes"""

ASYNC_READ: str = "async_read"
ASYNC_WRITE: str = "async_write"
SYNC_READ: str = "sync_read"
SYNC_WRITE: str = "sync_write"
TIME: str = "time"

ALL_MODES: list[str] = [ASYNC_WRITE, ASYNC_READ, SYNC_WRITE, SYNC_READ, TIME]

MODE_STRING_BY_MODE: dict[str, str] = {
    ASYNC_READ: "Async read",
    ASYNC_WRITE: "Async write",
    SYNC_READ: "Sync read",
    SYNC_WRITE: "Sync write",
    TIME: "Time",
}
