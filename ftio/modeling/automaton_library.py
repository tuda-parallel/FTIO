"""
AutomatonLibrary: directory-based store for compiled reference automata.

Files are stored as:  <library_dir>/<app_name>/ranks_<rank_key>.json

The rank_key encodes the application's rank configuration:
  - Fixed ranks: "128"
  - Malleable:   "16_32_128"  (state-by-state rank sequence, duplicates collapsed)

Author: Ahmad Tarraf
Copyright (c) 2024-2026 TU Darmstadt, Germany
Licensed under the BSD 3-Clause License.
"""

from __future__ import annotations

import glob
import json
import os

from ftio.modeling.reference_automaton import ReferenceAutomaton


class AutomatonLibrary:
    """
    Directory-based library of compiled reference automata, one file per
    (app_name, rank_key) pair.

    On the first run for an app+config, the automaton is saved as-is (std = 0).
    On each subsequent run with matching topology, distributions are updated
    using pooled statistics so timing estimates improve over time.
    """

    def __init__(self, directory: str):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def _app_dir(self, app_name: str) -> str:
        return os.path.join(self.directory, app_name)

    def _path(self, app_name: str, rank_key: str) -> str:
        return os.path.join(self._app_dir(app_name), f"ranks_{rank_key}.json")

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def available_apps(self) -> list[str]:
        try:
            return [
                d
                for d in os.listdir(self.directory)
                if os.path.isdir(os.path.join(self.directory, d))
            ]
        except OSError:
            return []

    def available_rank_keys(self, app_name: str) -> list[str]:
        app_dir = self._app_dir(app_name)
        if not os.path.isdir(app_dir):
            return []
        keys = []
        for f in glob.glob(os.path.join(app_dir, "ranks_*.json")):
            name = os.path.basename(f)
            key = name[len("ranks_") : -len(".json")]
            keys.append(key)
        return keys

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self, app_name: str, rank_key: str) -> ReferenceAutomaton | None:
        """Load reference for app + rank_key.

        Falls back to the nearest available rank configuration (by initial
        rank count) if an exact match is not found.
        """
        path = self._path(app_name, rank_key)
        if os.path.exists(path):
            return self._load_file(path)

        available = self.available_rank_keys(app_name)
        if not available:
            return None

        try:
            target_initial = int(rank_key.split("_")[0])
        except ValueError:
            return None

        def _initial(k: str) -> int:
            try:
                return int(k.split("_")[0])
            except ValueError:
                return -1

        nearest_key = min(available, key=lambda k: abs(_initial(k) - target_initial))
        fallback_path = self._path(app_name, nearest_key)
        ref = self._load_file(fallback_path)
        if ref is not None:
            print(
                f"[AutomatonLibrary] No exact match for {app_name}/ranks_{rank_key}; "
                f"using nearest: ranks_{nearest_key}"
            )
        return ref

    def _load_file(self, path: str) -> ReferenceAutomaton | None:
        try:
            with open(path) as fh:
                data = json.load(fh)
        except OSError as exc:
            print(f"[AutomatonLibrary] Could not read {path}: {exc}")
            return None
        except json.JSONDecodeError as exc:
            print(f"[AutomatonLibrary] JSON parse error in {path}: {exc}")
            return None

        # Detect format: our compact reference dict vs a raw PhaseAutomaton export.
        # The compact format stores "period_mean" at the state level.
        first_state = (data.get("states") or [{}])[0]
        if "period_mean" in first_state:
            return ReferenceAutomaton.from_dict(data)

        # Raw PhaseAutomaton export — derive app_name and rank_key from the path
        parts = path.replace("\\", "/").split("/")
        app_name = parts[-2] if len(parts) >= 2 else "unknown"
        rank_key = parts[-1][len("ranks_") : -len(".json")]
        return ReferenceAutomaton.from_automaton_dict(data, app_name, rank_key)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, automaton, app_name: str, rank_key: str) -> None:
        """Save a PhaseAutomaton to the library.

        If a reference already exists for this app + rank_key and its topology
        matches (same number of states), the new run is merged into the
        existing distributions.  Otherwise the new run is saved as a fresh
        reference — the old file is preserved under a timestamped name to
        avoid accidental data loss.
        """
        new_ref = ReferenceAutomaton.from_automaton_dict(
            automaton.to_dict(), app_name, rank_key
        )

        existing = self.load(app_name, rank_key)
        if existing is not None and existing.rank_key == rank_key:
            merged = existing.merge(new_ref)
            if merged is existing:
                # Topology mismatch — save new run under a versioned key
                import time

                versioned_key = f"{rank_key}_v{int(time.time())}"
                versioned_path = self._path(app_name, versioned_key)
                app_dir = self._app_dir(app_name)
                os.makedirs(app_dir, exist_ok=True)
                with open(versioned_path, "w") as fh:
                    json.dump(new_ref.to_dict(), fh, indent=2)
                print(
                    f"[AutomatonLibrary] Topology mismatch for {app_name}/ranks_{rank_key}; "
                    f"saved new run as ranks_{versioned_key}"
                )
                return
        else:
            merged = new_ref

        app_dir = self._app_dir(app_name)
        os.makedirs(app_dir, exist_ok=True)
        path = self._path(app_name, rank_key)
        with open(path, "w") as fh:
            json.dump(merged.to_dict(), fh, indent=2)
        print(
            f"[AutomatonLibrary] Saved {app_name}/ranks_{rank_key} → {path} "
            f"({merged.run_count} run(s), {merged.n_states} states)"
        )
