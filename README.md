# ElevatorOS

A real-time multi-elevator dispatch simulation and algorithm benchmarking platform.

## Project Structure

```
ElevatorOS/
├── backend/
│   ├── app/
│   │   ├── simulation/    # Core domain models & clock
│   │   ├── algorithms/    # Dispatch strategies (future)
│   │   ├── traffic/       # Passenger generation (future)
│   │   ├── metrics/       # KPI tracking (future)
│   │   └── api/           # FastAPI routes (future)
│   └── tests/             # pytest test suite
├── frontend/              # React + TypeScript app (future)
├── docs/                  # Documentation
├── benchmarks/            # Benchmark scripts & results
└── README.md
```

## Current Status: Milestone 1

Core simulation foundation — domain models and deterministic clock.

## Getting Started

### Prerequisites

- Python 3.11+
- pip

### Install & Test

```bash
cd backend
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Architecture Principles

- **Simulation is independent** — no coupling to API or UI frameworks.
- **Algorithms are interchangeable** — dispatch strategies plug in via a common interface.
- **Clock is deterministic** — tick-based, reproducible, no wall-clock dependency.
- **Models are clean** — dataclasses with validation, no hidden side effects.

## License

MIT
