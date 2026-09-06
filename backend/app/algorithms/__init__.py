"""Dispatch algorithms for elevator scheduling.

This package contains interchangeable dispatch algorithms that
assign hall-call requests to elevators. Each algorithm implements
the ``DispatchAlgorithm`` interface from ``base.py``.

Available algorithms:
    - ``FCFSDispatch``: First-Come, First-Served (baseline).
"""

from app.algorithms.base import DispatchAlgorithm, DispatchResult
from app.algorithms.fcfs import FCFSDispatch

__all__ = ["DispatchAlgorithm", "DispatchResult", "FCFSDispatch"]
