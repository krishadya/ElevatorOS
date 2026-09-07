import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "./api/client";
import type { SimulationState } from "./api/types";
import App from "./App";

vi.mock("./api/client", () => ({
  getState: vi.fn(),
  createHallCall: vi.fn(),
  createCarRequest: vi.fn(),
  tick: vi.fn(),
  reset: vi.fn(),
  setAlgorithm: vi.fn(),
}));

const baseState: SimulationState = {
  tick: 0,
  time: 0,
  algorithm: "fcfs",
  elevators: [
    {
      id: "E1",
      current_floor: 1,
      direction: "IDLE",
      state: "IDLE",
      door_state: "CLOSED",
      stops: [],
    },
    {
      id: "E2",
      current_floor: 1,
      direction: "IDLE",
      state: "IDLE",
      door_state: "CLOSED",
      stops: [],
    },
  ],
  active_hall_calls: [],
  recent_events: [],
};

const mockedApi = vi.mocked(api);

function renderApp(state: SimulationState = baseState): void {
  mockedApi.getState.mockResolvedValue(state);
  mockedApi.tick.mockResolvedValue({ ...state, tick: state.tick + 1, time: state.time + 1 });
  mockedApi.reset.mockResolvedValue(baseState);
  mockedApi.createHallCall.mockResolvedValue({
    hall_call: {
      id: "HC1",
      floor: 6,
      direction: "UP",
      assigned_elevator: "E1",
    },
    assignment: { elevator_id: "E1" },
  });
  mockedApi.createCarRequest.mockResolvedValue({
    car_request: { id: "CR1", elevator_id: "E1", destination_floor: 7 },
    stops: [7],
  });
  mockedApi.setAlgorithm.mockResolvedValue({ algorithm: "nearest" });
  render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ElevatorOS visualizer", () => {
  it("omits impossible hall-call directions at the building bounds", async () => {
    renderApp();
    await screen.findByText("Floor 1");

    expect(screen.queryByRole("button", { name: "Hall call DOWN at floor 1" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Hall call UP at floor 10" })).not.toBeInTheDocument();
  });

  it("sends hall calls through the typed API client", async () => {
    renderApp();
    await screen.findByText("Floor 6");

    fireEvent.click(screen.getByRole("button", { name: "Hall call UP at floor 6" }));

    await waitFor(() => expect(mockedApi.createHallCall).toHaveBeenCalledWith(6, "UP"));
  });

  it("changes the algorithm through the typed API client", async () => {
    renderApp();
    await screen.findByText("Floor 1");

    fireEvent.change(screen.getByLabelText("Dispatch algorithm"), {
      target: { value: "nearest" },
    });

    await waitFor(() => expect(mockedApi.setAlgorithm).toHaveBeenCalledWith("nearest"));
  });

  it("explains the selected dispatch algorithm", async () => {
    renderApp();
    await screen.findByText("Floor 1");

    fireEvent.click(screen.getByRole("button", { name: "About the selected dispatch algorithm" }));
    expect(screen.getByRole("heading", { name: "First-Come, First-Served (FCFS)" })).toBeInTheDocument();

    mockedApi.getState.mockResolvedValue({ ...baseState, algorithm: "nearest" });
    fireEvent.change(screen.getByLabelText("Dispatch algorithm"), {
      target: { value: "nearest" },
    });

    expect(await screen.findByRole("heading", { name: "Nearest Suitable Car" })).toBeInTheDocument();
    expect(screen.getByText(/moving the wrong way/)).toBeInTheDocument();
  });

  it("steps the simulation exactly once", async () => {
    renderApp();
    await screen.findByText("Floor 1");

    fireEvent.click(screen.getByRole("button", { name: "Step" }));

    await waitFor(() => expect(mockedApi.tick).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/Tick 1/)).toBeInTheDocument();
    expect(screen.getByText("Paused")).toBeInTheDocument();
  });

  it("resets through the API and restores the returned state", async () => {
    renderApp({ ...baseState, tick: 4, time: 4, algorithm: "nearest" });
    await screen.findByText(/Tick 4/);

    fireEvent.click(screen.getByRole("button", { name: "Reset" }));

    await waitFor(() => expect(mockedApi.reset).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/Tick 0/)).toBeInTheDocument();
  });

  it("shows destination controls only for elevators with open doors", async () => {
    renderApp();
    await screen.findByText("Floor 1");
    expect(screen.queryByRole("heading", { name: "Inside Elevator" })).not.toBeInTheDocument();

    const openState: SimulationState = {
      ...baseState,
      elevators: [
        { ...baseState.elevators[0], state: "STOPPED", door_state: "OPEN" },
        baseState.elevators[1],
      ],
    };
    renderApp(openState);

    expect(await screen.findByRole("heading", { name: "E1 — Select Destination" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "E1 destination floor 7" })).toBeInTheDocument();
  });

  it("targets the open elevator when selecting a destination", async () => {
    const openState: SimulationState = {
      ...baseState,
      elevators: [
        { ...baseState.elevators[0], state: "STOPPED", door_state: "OPEN" },
        baseState.elevators[1],
      ],
    };
    renderApp(openState);

    fireEvent.click(await screen.findByRole("button", { name: "E1 destination floor 7" }));

    await waitFor(() => expect(mockedApi.createCarRequest).toHaveBeenCalledWith("E1", 7));
  });

  it("highlights active calls and displays their assigned elevator", async () => {
    renderApp({
      ...baseState,
      active_hall_calls: [
        { id: "HC1", floor: 6, direction: "UP", assigned_elevator: "E1" },
      ],
    });

    await screen.findByText("Floor 6");
    const activeCall = document.querySelector(".floor-row.has-active-call .active-call");

    expect(activeCall).toHaveTextContent("↑");
    expect(activeCall).toHaveTextContent("E1");
    expect(screen.getByRole("button", { name: "Hall call UP at floor 6" })).toHaveClass("is-active");
  });
});
