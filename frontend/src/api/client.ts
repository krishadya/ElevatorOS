import type {
  AlgorithmName,
  CarRequestResponse,
  HallCallResponse,
  HallDirection,
  SimulationState,
} from "./types";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getState(): Promise<SimulationState> {
  return request<SimulationState>("/state");
}

export function createHallCall(
  floor: number,
  direction: HallDirection,
): Promise<HallCallResponse> {
  return request<HallCallResponse>("/hall-call", {
    method: "POST",
    body: JSON.stringify({ floor, direction }),
  });
}

export function createCarRequest(
  elevatorId: string,
  destinationFloor: number,
): Promise<CarRequestResponse> {
  return request<CarRequestResponse>("/car-request", {
    method: "POST",
    body: JSON.stringify({
      elevator_id: elevatorId,
      destination_floor: destinationFloor,
    }),
  });
}

export function tick(): Promise<SimulationState> {
  return request<SimulationState>("/tick", { method: "POST" });
}

export function reset(): Promise<SimulationState> {
  return request<SimulationState>("/reset", { method: "POST" });
}

export function setAlgorithm(
  algorithm: AlgorithmName,
): Promise<{ algorithm: AlgorithmName }> {
  return request<{ algorithm: AlgorithmName }>("/algorithm", {
    method: "POST",
    body: JSON.stringify({ algorithm }),
  });
}
