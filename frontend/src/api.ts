import type { PredictionResponse, SystemStatus, VesselDetail, VesselPosition } from "./types";

const configuredApiBase = import.meta.env.VITE_API_URL as string | undefined;
const configuredWsBase = import.meta.env.VITE_WS_URL as string | undefined;
const sameOriginWsBase = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;

export const API_BASE_URL = configuredApiBase || (import.meta.env.DEV ? "" : "http://localhost:8000");
export const WS_BASE_URL =
  configuredWsBase ||
  (import.meta.env.DEV
    ? sameOriginWsBase
    : API_BASE_URL.replace(/^http:\/\//, "ws://").replace(/^https:\/\//, "wss://"));

async function requestJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function fetchVessels(signal?: AbortSignal): Promise<VesselPosition[]> {
  return requestJson<VesselPosition[]>("/api/vessels", signal);
}

export function fetchVesselDetail(mmsi: string, signal?: AbortSignal): Promise<VesselDetail> {
  return requestJson<VesselDetail>(`/api/vessels/${encodeURIComponent(mmsi)}`, signal);
}

export function fetchVesselHistory(mmsi: string, signal?: AbortSignal): Promise<VesselPosition[]> {
  return requestJson<VesselPosition[]>(`/api/vessels/${encodeURIComponent(mmsi)}/history`, signal);
}

export function fetchVesselPrediction(mmsi: string, signal?: AbortSignal): Promise<PredictionResponse> {
  return requestJson<PredictionResponse>(`/api/vessels/${encodeURIComponent(mmsi)}/prediction`, signal);
}

export function fetchSystemStatus(signal?: AbortSignal): Promise<SystemStatus> {
  return requestJson<SystemStatus>("/api/system/status", signal);
}
