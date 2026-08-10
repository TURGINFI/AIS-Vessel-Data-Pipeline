import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Anchor, Clock3 } from "lucide-react";

import { fetchSystemStatus, fetchVesselHistory, fetchVesselPrediction, fetchVessels } from "./api";
import { MapView } from "./components/MapView";
import { StatusBar } from "./components/StatusBar";
import { VesselList } from "./components/VesselList";
import { VesselPanel } from "./components/VesselPanel";
import { useVesselStream } from "./hooks/useVesselStream";
import type { PredictionResponse, SystemStatus, VesselPosition, VesselUpdateMessage } from "./types";

export default function App() {
  const [vesselsByMmsi, setVesselsByMmsi] = useState<Record<string, VesselPosition>>({});
  const [selectedMmsi, setSelectedMmsi] = useState<string | null>(null);
  const [history, setHistory] = useState<VesselPosition[]>([]);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [autoFollow, setAutoFollow] = useState(true);
  const [lastRefreshError, setLastRefreshError] = useState<string | null>(null);
  const pendingUpdatesRef = useRef<Record<string, VesselPosition>>({});
  const updateFlushTimerRef = useRef<number | undefined>();

  const mergeVessels = useCallback((positions: VesselPosition[]) => {
    setVesselsByMmsi((current) => {
      const next = { ...current };
      positions.forEach((position) => {
        next[position.mmsi] = position;
      });
      return next;
    });
  }, []);

  const handleVesselUpdate = useCallback(
    (message: VesselUpdateMessage) => {
      pendingUpdatesRef.current[message.data.mmsi] = message.data;
      if (updateFlushTimerRef.current !== undefined) {
        return;
      }
      updateFlushTimerRef.current = window.setTimeout(() => {
        const positions = Object.values(pendingUpdatesRef.current);
        pendingUpdatesRef.current = {};
        updateFlushTimerRef.current = undefined;
        mergeVessels(positions);
      }, 250);
    },
    [mergeVessels]
  );

  const connectionStatus = useVesselStream(handleVesselUpdate);

  useEffect(() => {
    return () => {
      if (updateFlushTimerRef.current !== undefined) {
        window.clearTimeout(updateFlushTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchVessels(controller.signal)
      .then((positions) => {
        mergeVessels(positions);
        setLastRefreshError(null);
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setLastRefreshError(error instanceof Error ? error.message : "Unable to load vessels");
        }
      });
    return () => controller.abort();
  }, [mergeVessels]);

  useEffect(() => {
    const controller = new AbortController();

    const refreshStatus = () => {
      fetchSystemStatus(controller.signal)
        .then(setSystemStatus)
        .catch(() => undefined);
    };

    refreshStatus();
    const timer = window.setInterval(refreshStatus, 5000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (connectionStatus === "connected") {
      return;
    }

    const controller = new AbortController();
    const timer = window.setInterval(() => {
      fetchVessels(controller.signal)
        .then((positions) => {
          mergeVessels(positions);
          setLastRefreshError(null);
        })
        .catch((error) => {
          if (!controller.signal.aborted) {
            setLastRefreshError(error instanceof Error ? error.message : "Unable to refresh vessels");
          }
        });
    }, 10000);

    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [connectionStatus, mergeVessels]);

  const vessels = useMemo(
    () =>
      Object.values(vesselsByMmsi).sort((a, b) =>
        (a.vessel_name || a.mmsi).localeCompare(b.vessel_name || b.mmsi)
      ),
    [vesselsByMmsi]
  );

  const visibleVessels = useMemo(() => {
    const search = searchTerm.trim().toLowerCase();
    if (!search) {
      return vessels;
    }
    return vessels.filter((vessel) => {
      const name = vessel.vessel_name?.toLowerCase() || "";
      return vessel.mmsi.includes(search) || name.includes(search);
    });
  }, [searchTerm, vessels]);

  const selectedVessel = selectedMmsi ? vesselsByMmsi[selectedMmsi] ?? null : null;
  const selectedTimestamp = selectedVessel?.timestamp;

  useEffect(() => {
    if (!selectedMmsi) {
      setHistory([]);
      setPrediction(null);
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      Promise.all([
        fetchVesselHistory(selectedMmsi, controller.signal),
        fetchVesselPrediction(selectedMmsi, controller.signal)
      ])
        .then(([historyResponse, predictionResponse]) => {
          setHistory(historyResponse);
          setPrediction(predictionResponse);
          setLastRefreshError(null);
        })
        .catch((error) => {
          if (!controller.signal.aborted) {
            setLastRefreshError(error instanceof Error ? error.message : "Unable to load vessel trajectory");
          }
        });
    }, 150);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [selectedMmsi, selectedTimestamp]);

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div className="brand">
          <span className="brand-mark">
            <Anchor size={21} />
          </span>
          <div>
            <strong>AIS Trajectory Predictor</strong>
            <span>Public AIS and replay maritime tracking dashboard</span>
          </div>
        </div>
        <div className="top-time">
          <Clock3 size={16} />
          <span>{new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(new Date())}</span>
        </div>
      </header>

      <main className="dashboard">
        <div className="map-panel">
          <MapView
            vessels={visibleVessels}
            selectedMmsi={selectedMmsi}
            history={history}
            prediction={prediction?.points ?? []}
            autoFollow={autoFollow}
            onSelectVessel={setSelectedMmsi}
          />
          <StatusBar connectionStatus={connectionStatus} systemStatus={systemStatus} />
          <div className="map-legend">
            <span>
              <i className="legend-dot current" />
              Current vessel
            </span>
            <span>
              <i className="legend-line history" />
              Historical route
            </span>
            <span>
              <i className="legend-line prediction" />
              Predicted route
            </span>
          </div>
          {lastRefreshError && <div className="error-toast">{lastRefreshError}</div>}
        </div>

        <div className="side-rail">
          <VesselList
            vessels={visibleVessels}
            selectedMmsi={selectedMmsi}
            searchTerm={searchTerm}
            onSearchTermChange={setSearchTerm}
            onSelectVessel={setSelectedMmsi}
          />
          <VesselPanel
            selectedVessel={selectedVessel}
            historyCount={history.length}
            prediction={prediction}
            autoFollow={autoFollow}
            onAutoFollowChange={setAutoFollow}
          />
        </div>
      </main>
    </div>
  );
}
