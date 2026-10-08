"use client";

import { useEffect, useMemo } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { MapMode } from "./FloodMap";
import { assetEmoji, formatKes } from "@/lib/format";

type Point = {
  id: string;
  lat: number;
  lon: number;
  asset: string;
  housing: string;
  value_kes: number;
  hazard_severe: number;
  insured: boolean;
  confidence: string;
  synthetic: boolean;
  depth: number;
};

type Hotspot = { name: string; lat: number; lon: number };

type Props = {
  mode: MapMode;
  points: Point[];
  hotspots: Hotspot[];
  selectedId: string | null;
  onSelect: (id: string) => void;
};

function FitNairobi() {
  const map = useMap();
  useEffect(() => {
    map.setView([-1.286389, 36.817223], 11);
  }, [map]);
  return null;
}

function markerIcon(point: Point, mode: MapMode, selected: boolean) {
  const emoji = assetEmoji(point.asset);
  const dim =
    mode === "quality" && point.confidence !== "high"
      ? "ft-marker--dim"
      : "";
  const html = `<div class="ft-marker ${dim} ${selected ? "ring-2 ring-accent" : ""}">${emoji}</div>`;
  return L.divIcon({
    className: "",
    html,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

function depthColor(depth: number): string {
  if (depth >= 2.5) return "#1e1b4b";
  if (depth >= 1.5) return "#1d4ed8";
  if (depth >= 0.8) return "#38bdf8";
  if (depth >= 0.3) return "#bae6fd";
  return "transparent";
}

export default function LeafletInner({
  mode,
  points,
  hotspots,
  selectedId,
  onSelect,
}: Props) {
  const floodCircles = useMemo(
    () =>
      points
        .filter((p) => p.depth > 0.25)
        .map((p) => ({
          ...p,
          radius: 80 + p.depth * 90,
          color: depthColor(p.depth),
        })),
    [points],
  );

  return (
    <MapContainer
      center={[-1.286389, 36.817223]}
      zoom={11}
      scrollWheelZoom
      className="h-full w-full"
    >
      <FitNairobi />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />

      {(mode === "overview" || mode === "hazard" || mode === "loss" || mode === "risk") &&
        floodCircles.map((p) => (
          <CircleMarker
            key={`flood-${p.id}`}
            center={[p.lat, p.lon]}
            radius={Math.min(28, 6 + p.depth * 6)}
            pathOptions={{
              color: p.color,
              fillColor: p.color,
              fillOpacity: 0.35,
              weight: 0,
            }}
          />
        ))}

      {hotspots.map((h) => (
        <Marker
          key={`hs-${h.name}-${h.lat}`}
          position={[h.lat, h.lon]}
          icon={L.divIcon({
            className: "",
            html: `<div class="ft-marker ft-marker--hotspot">⚠</div>`,
            iconSize: [34, 34],
            iconAnchor: [17, 17],
          })}
        >
          <Popup>
            <strong>{h.name}</strong>
            <br />
            Known flood-prone area
          </Popup>
        </Marker>
      ))}

      {points.map((p) => (
        <Marker
          key={p.id}
          position={[p.lat, p.lon]}
          icon={markerIcon(p, mode, selectedId === p.id)}
          eventHandlers={{ click: () => onSelect(p.id) }}
        >
          <Popup>
            <strong>{p.id}</strong>
            <br />
            {formatKes(p.value_kes)}
            <br />
            Depth ~ {p.depth.toFixed(1)} m
            {mode === "quality" ? (
              <>
                <br />
                Confidence: {p.confidence}
              </>
            ) : null}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
