export interface VesselPosition {
  mmsi: string;
  latitude: number;
  longitude: number;
  timestamp: string;
  speed: number | null;
  course: number | null;
  heading: number | null;
  vessel_name: string | null;
  vessel_type: string | null;
  source: string;
}

export interface VesselDetail {
  latest_position: VesselPosition;
  history_count: number;
}

export interface PredictionPoint {
  latitude: number;
  longitude: number;
  timestamp: string;
  seconds_ahead: number;
  confidence: number;
}

export interface PredictionResponse {
  mmsi: string;
  horizon_seconds: number;
  step_seconds: number;
  model: string;
  points: PredictionPoint[];
}

export interface SystemStatus {
  provider: string;
  ingestion_running: boolean;
  websocket_clients: number;
  active_vessels: number;
  stored_positions: number;
  received_messages: number;
  stored_messages: number;
  rejected_messages: number;
  last_message_at: string | null;
  target_delay_seconds: number;
}

export interface VesselUpdateMessage {
  type: "vessel_update";
  data: VesselPosition;
}

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

