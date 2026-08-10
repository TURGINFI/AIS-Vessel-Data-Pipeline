import { Activity, Database, Radio, Wifi, WifiOff } from "lucide-react";

import type { ConnectionStatus, SystemStatus } from "../types";

interface StatusBarProps {
  connectionStatus: ConnectionStatus;
  systemStatus: SystemStatus | null;
}

export function StatusBar({ connectionStatus, systemStatus }: StatusBarProps) {
  const connected = connectionStatus === "connected";

  return (
    <div className="status-bar">
      <div className={`connection-pill ${connected ? "connected" : ""}`}>
        {connected ? <Wifi size={16} /> : <WifiOff size={16} />}
        <span>{connectionStatus}</span>
      </div>
      <StatusItem icon={<Radio size={16} />} label="Provider" value={systemStatus?.provider || "replay"} />
      <StatusItem icon={<Activity size={16} />} label="Vessels" value={String(systemStatus?.active_vessels ?? 0)} />
      <StatusItem icon={<Database size={16} />} label="Stored points" value={String(systemStatus?.stored_positions ?? 0)} />
    </div>
  );
}

function StatusItem({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="status-item">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

