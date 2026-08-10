import { Search } from "lucide-react";

import type { VesselPosition } from "../types";

interface VesselListProps {
  vessels: VesselPosition[];
  selectedMmsi: string | null;
  searchTerm: string;
  onSearchTermChange: (value: string) => void;
  onSelectVessel: (mmsi: string) => void;
}

export function VesselList({
  vessels,
  selectedMmsi,
  searchTerm,
  onSearchTermChange,
  onSelectVessel
}: VesselListProps) {
  return (
    <aside className="panel vessel-list-panel">
      <div className="panel-kicker">Live traffic</div>
      <h2>Tracked vessels</h2>
      <label className="search-box">
        <Search size={17} />
        <input
          value={searchTerm}
          onChange={(event) => onSearchTermChange(event.target.value)}
          placeholder="Search MMSI or vessel name"
        />
      </label>
      <div className="vessel-list">
        {vessels.map((vessel) => (
          <button
            key={vessel.mmsi}
            className={`vessel-row ${vessel.mmsi === selectedMmsi ? "selected" : ""}`}
            onClick={() => onSelectVessel(vessel.mmsi)}
            type="button"
          >
            <span>
              <strong>{vessel.vessel_name || "Unnamed vessel"}</strong>
              <small>{vessel.mmsi}</small>
            </span>
            <em>{vessel.speed === null ? "n/a" : `${vessel.speed.toFixed(1)} kn`}</em>
          </button>
        ))}
      </div>
    </aside>
  );
}

