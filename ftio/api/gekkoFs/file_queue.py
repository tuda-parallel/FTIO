"""
This file provides a multiprocessing-safe queue implementation for managing file paths,
ensuring that files are processed exactly once across multiple worker processes.

The FileQueue class uses shared memory data structures to enable safe concurrent access
and includes methods for adding, retrieving, and marking files as processed or failed.

Author: Ahmad Tarraf  
Copyright (c) 2025 TU Darmstadt, Germany  
Date: Apr 2025  

Licensed under the BSD 3-Clause License.  
For more information, see the LICENSE file in the project root:  
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from multiprocessing import Manager


class FileQueue:
    """
    A multiprocessing-safe queue for file paths, ensuring that files are
    processed exactly once across multiple worker processes.

    Internally uses a manager-backed shared list and a lock to guard multi-step operations.
    """

    def __init__(self) -> None:
        """
        Initialize the FileQueue with shared memory data structures.
        """
        m = Manager()
        self._queue = m.list()
        self._lock = m.Lock()

    def put(self, item: str) -> None:
        """
        Add a file path to the queue if it's not already present and not being processed.

        Args:
            item: The file path to queue.
        """
        with self._lock:
            if item not in self._queue:
                self._queue.append(item)

    def get_next(self) -> str | None:
        """
        Get the next file to process that is currently in the queue.

        Returns:
            A file path string if available, otherwise None.
        """
        with self._lock:
            if self._queue:
                return self._queue.pop(0)
            return None

    def mark_done(self, item: str) -> None:
        """
        Mark a file as successfully processed and remove it from the queue.

        Args:
            item: The file path to mark as done.
        """
        with self._lock:
            if item in self._queue:
                self._queue.remove(item)

    def mark_failed(self, item: str) -> None:
        """
        Mark a file as failed and remove it from the queue.

        Args:
            item: The file path to mark as failed.
        """
        # TODO: Implement a retry mechanism or logging for failed items.
        with self._lock:
            if item in self._queue:
                self._queue.remove(item)

    def in_progress(self, item: str) -> bool:
        """
        Check if the file path is currently in the queue.

        Args:
            item: The file path to check.

        Returns:
            True if the file exists in the queue, otherwise False.
        """
        with self._lock:
            return item in self._queue

    def __len__(self) -> int:
        """
        Get the number of items currently in the queue.

        Returns:
            The number of file paths in the queue.
        """
        return len(self._queue)

    def __str__(self) -> str:
        """
        Get a string representation of the queue.

        Returns:
            A string representation of the queue contents.
        """
        return f"FileQueue(queue size={len(self._queue)}, contents={list(self._queue)})"
