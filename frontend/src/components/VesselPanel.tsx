import { Crosshair, History, LocateFixed, Navigation, RadioTower, Route } from "lucide-react";

import type { PredictionResponse, VesselPosition } from "../types";

interface VesselPanelProps {
  selectedVessel: VesselPosition | null;
  historyCount: number;
  prediction: PredictionResponse | null;
  autoFollow: boolean;
  onAutoFollowChange: (enabled: boolean) => void;
}

export function VesselPanel({
  selectedVessel,
  historyCount,
  prediction,
  autoFollow,
  onAutoFollowChange
}: VesselPanelProps) {
  if (!selectedVessel) {
    return (
      <aside className="panel vessel-panel">
        <div className="panel-kicker">Selection</div>
        <h2>Choose a vessel</h2>
        <p className="muted">
          Click a marker or a vessel row to inspect recent AIS history and the predicted route.
        </p>
        <div className="empty-state">
          <Navigation size={34} />
          <span>Waiting for a selected vessel</span>
        </div>
      </aside>
    );
  }

  const predictionHorizon = prediction ? `${Math.round(prediction.horizon_seconds / 60)} min` : "Pending";

  return (
    <aside className="panel vessel-panel">
      <div className="panel-header-row">
        <div>
          <div className="panel-kicker">Selected vessel</div>
          <h2>{selectedVessel.vessel_name || "Unnamed vessel"}</h2>
        </div>
        <span className="type-badge">{selectedVessel.vessel_type || "Unknown"}</span>
      </div>

      <div className="metrics-grid">
        <Metric label="MMSI" value={selectedVessel.mmsi} icon={<RadioTower size={17} />} />
        <Metric label="Speed" value={formatSpeed(selectedVessel.speed)} icon={<Navigation size={17} />} />
        <Metric label="Course" value={formatDegrees(selectedVessel.course)} icon={<Crosshair size={17} />} />
        <Metric label="Heading" value={formatDegrees(selectedVessel.heading)} icon={<LocateFixed size={17} />} />
      </div>

      <div className="detail-list">
        <Detail label="Last update" value={formatTimestamp(selectedVessel.timestamp)} />
        <Detail label="Coordinates" value={`${selectedVessel.latitude.toFixed(5)}, ${selectedVessel.longitude.toFixed(5)}`} />
        <Detail label="AIS source" value={selectedVessel.source} />
        <Detail label="History points" value={historyCount.toString()} icon={<History size={15} />} />
        <Detail label="Prediction horizon" value={predictionHorizon} icon={<Route size={15} />} />
      </div>

      <label className="toggle-row">
        <input
          type="checkbox"
          checked={autoFollow}
          onChange={(event) => onAutoFollowChange(event.target.checked)}
        />
        <span>Auto-follow selected vessel</span>
      </label>
    </aside>
  );
}

function Metric({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="metric">
      <div className="metric-icon">{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function Detail({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="detail-row">
      <span>
        {icon}
        {label}
      </span>
      <strong>{value}</strong>
    </div>
  );
}

function formatSpeed(speed: number | null): string {
  return speed === null ? "Unknown" : `${speed.toFixed(1)} kn`;
}

function formatDegrees(value: number | null): string {
  return value === null ? "Unknown" : `${Math.round(value)} deg`;
}

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(new Date(value));
}

