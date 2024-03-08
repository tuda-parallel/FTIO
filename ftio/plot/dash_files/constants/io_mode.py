"""Input/output modes"""

ASYNC_READ: str = "read_async"
ASYNC_WRITE: str = "write_async"
SYNC_READ: str = "read_sync"
SYNC_WRITE: str = "write_sync"
TIME: str = "time"

ALL_MODES: list[str] = [ASYNC_WRITE, ASYNC_READ, SYNC_WRITE, SYNC_READ, TIME]

MODE_STRING_BY_MODE: dict[str, str] = {
    ASYNC_READ: "Async read",
    ASYNC_WRITE: "Async write",
    SYNC_READ: "Sync read",
    SYNC_WRITE: "Sync write",
    TIME: "Time",
}
