"""Dispatch algorithms for elevator scheduling.

This package contains interchangeable dispatch algorithms that
assign hall-call requests to elevators. Each algorithm implements
the ``DispatchAlgorithm`` interface from ``base.py``.

Available algorithms:
    - ``FCFSDispatch``: First-Come, First-Served (baseline).
    - ``NearestSuitableCarDispatch``: Direction-aware suitability ranking.
"""

from app.algorithms.base import DispatchAlgorithm, DispatchResult
from app.algorithms.fcfs import FCFSDispatch
from app.algorithms.nearest_car import NearestSuitableCarDispatch

__all__ = [
    "DispatchAlgorithm",
    "DispatchResult",
    "FCFSDispatch",
    "NearestSuitableCarDispatch",
]
