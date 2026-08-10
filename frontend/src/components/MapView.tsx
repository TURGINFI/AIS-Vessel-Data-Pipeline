import L from "leaflet";
import { useEffect, useRef } from "react";

import type { PredictionPoint, VesselPosition } from "../types";

interface MapViewProps {
  vessels: VesselPosition[];
  selectedMmsi: string | null;
  history: VesselPosition[];
  prediction: PredictionPoint[];
  autoFollow: boolean;
  onSelectVessel: (mmsi: string) => void;
}

const DEFAULT_CENTER: L.LatLngExpression = [59.92, 24.82];
const CANVAS_MARKER_THRESHOLD = 750;
type VesselLayer = L.Marker | L.CircleMarker;

export function MapView({
  vessels,
  selectedMmsi,
  history,
  prediction,
  autoFollow,
  onSelectVessel
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, VesselLayer>>(new Map());
  const markerModeRef = useRef<"arrow" | "canvas">("arrow");
  const historyLineRef = useRef<L.Polyline | null>(null);
  const predictionLineRef = useRef<L.Polyline | null>(null);
  const hasFitInitialBoundsRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const map = L.map(containerRef.current, {
      center: DEFAULT_CENTER,
      zoom: 9,
      zoomControl: false,
      preferCanvas: true
    });

    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const markerMode = vessels.length > CANVAS_MARKER_THRESHOLD ? "canvas" : "arrow";
    if (markerMode !== markerModeRef.current) {
      markersRef.current.forEach((marker) => marker.removeFrom(map));
      markersRef.current.clear();
      markerModeRef.current = markerMode;
    }

    const activeMmsis = new Set(vessels.map((vessel) => vessel.mmsi));

    vessels.forEach((vessel) => {
      const position: L.LatLngExpression = [vessel.latitude, vessel.longitude];
      const isSelected = vessel.mmsi === selectedMmsi;
      const existing = markersRef.current.get(vessel.mmsi);

      if (existing) {
        existing.setLatLng(position);
        if (existing instanceof L.Marker && markerMode === "arrow") {
          existing.setIcon(createVesselIcon(vessel, isSelected));
        }
        if (existing instanceof L.CircleMarker && markerMode === "canvas") {
          existing.setStyle(createCanvasMarkerStyle(isSelected));
        }
        existing.off("click");
        existing.on("click", () => onSelectVessel(vessel.mmsi));
        return;
      }

      const marker =
        markerMode === "canvas"
          ? L.circleMarker(position, createCanvasMarkerStyle(isSelected)).bindTooltip(vessel.vessel_name || vessel.mmsi)
          : L.marker(position, {
              icon: createVesselIcon(vessel, isSelected),
              keyboard: true,
              title: vessel.vessel_name || vessel.mmsi
            });
      marker.on("click", () => onSelectVessel(vessel.mmsi));
      marker.addTo(map);
      markersRef.current.set(vessel.mmsi, marker);
    });

    markersRef.current.forEach((marker, mmsi) => {
      if (!activeMmsis.has(mmsi)) {
        marker.removeFrom(map);
        markersRef.current.delete(mmsi);
      }
    });

    if (vessels.length > 0 && !hasFitInitialBoundsRef.current) {
      const bounds = L.latLngBounds(vessels.map((vessel) => [vessel.latitude, vessel.longitude]));
      map.fitBounds(bounds.pad(0.25), { animate: false });
      hasFitInitialBoundsRef.current = true;
    }
  }, [vessels, selectedMmsi, onSelectVessel]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    if (historyLineRef.current) {
      historyLineRef.current.removeFrom(map);
      historyLineRef.current = null;
    }
    if (history.length >= 2) {
      historyLineRef.current = L.polyline(
        history.map((point) => [point.latitude, point.longitude]),
        {
          color: "#0f8ca0",
          weight: 4,
          opacity: 0.85,
          lineCap: "round",
          lineJoin: "round"
        }
      ).addTo(map);
    }

    if (predictionLineRef.current) {
      predictionLineRef.current.removeFrom(map);
      predictionLineRef.current = null;
    }
    if (prediction.length >= 2) {
      predictionLineRef.current = L.polyline(
        prediction.map((point) => [point.latitude, point.longitude]),
        {
          color: "#f2a51a",
          weight: 4,
          opacity: 0.9,
          dashArray: "10 10",
          lineCap: "round",
          lineJoin: "round"
        }
      ).addTo(map);
    }
  }, [history, prediction]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !autoFollow || !selectedMmsi) {
      return;
    }
    const selected = vessels.find((vessel) => vessel.mmsi === selectedMmsi);
    if (selected) {
      map.panTo([selected.latitude, selected.longitude], { animate: true, duration: 0.6 });
    }
  }, [autoFollow, selectedMmsi, vessels]);

  return <div ref={containerRef} className="map-shell" aria-label="Interactive vessel tracking map" />;
}

function createVesselIcon(vessel: VesselPosition, selected: boolean): L.DivIcon {
  const heading = vessel.heading ?? vessel.course ?? 0;
  const label = vessel.vessel_name || vessel.mmsi;
  return L.divIcon({
    className: "vessel-marker-anchor",
    html: `
      <div class="vessel-marker ${selected ? "selected" : ""}" style="--heading:${heading}deg" aria-label="${escapeHtml(label)}">
        <div class="vessel-marker-arrow"></div>
      </div>
    `,
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  });
}

function createCanvasMarkerStyle(selected: boolean): L.CircleMarkerOptions {
  return {
    radius: selected ? 7 : 4,
    color: selected ? "#f2a51a" : "#053b46",
    weight: selected ? 3 : 1,
    fillColor: selected ? "#f2a51a" : "#18b6c8",
    fillOpacity: selected ? 0.95 : 0.75,
    opacity: 0.95
  };
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
