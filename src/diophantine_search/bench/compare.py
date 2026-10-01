"""Comparison helpers for benchmark result documents."""

from __future__ import annotations

from typing import Any


def _key(record: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        record["solver"],
        record["k"],
        record["bound"],
        record["mode"],
    )


def compare_runs(old: dict, new: dict) -> dict[str, Any]:
    """Compare matching result medians and report document differences."""

    old_results = {_key(record): record for record in old["results"]}
    new_results = {_key(record): record for record in new["results"]}
    shared = sorted(old_results.keys() & new_results.keys())
    matches = []
    for key in shared:
        old_median = old_results[key]["median_ns"]
        new_median = new_results[key]["median_ns"]
        matches.append(
            {
                "solver": key[0],
                "k": key[1],
                "bound": key[2],
                "mode": key[3],
                "old_median_ns": old_median,
                "new_median_ns": new_median,
                "speedup": old_median / new_median,
            }
        )

    ignored = {"timestamp_utc", "git_commit", "git_dirty"}
    old_environment = old.get("environment", {})
    new_environment = new.get("environment", {})
    environment_differences = sorted(
        key
        for key in old_environment.keys() | new_environment.keys()
        if key not in ignored
        and old_environment.get(key) != new_environment.get(key)
    )
    return {
        "matches": matches,
        "only_in_old": sorted(old_results.keys() - new_results.keys()),
        "only_in_new": sorted(new_results.keys() - old_results.keys()),
        "environment_differences": environment_differences,
    }
