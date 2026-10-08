"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import type {
  GeoJSONSource,
  Map as MapLibreMap,
  MapLayerMouseEvent,
  StyleSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { MapMode } from "./FloodMap";
import {
  boundsFromPoints,
  colorForFloodRisk,
  floodRiskScore,
  type PortfolioPoint,
} from "@/lib/map-portfolio";

export type { PortfolioPoint };
export type BasemapStyle = "streets" | "satellite";

type Hotspot = { name: string; lat: number; lon: number };

type Props = {
  mode: MapMode;
  basemap?: BasemapStyle;
  points: PortfolioPoint[];
  hotspots: Hotspot[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** When true, camera fits uploaded/live coordinates (any Kenyan city). */
  fitToData?: boolean;
};

const KENYA_FALLBACK: [number, number] = [36.82, -1.29];

/** Half-width of extruded footprint in degrees (~55 m). */
const FOOTPRINT = 0.0005;

function heightFromTiv(valueKes: number): number {
  // Log scale so 0.5M–840M maps to readable 12–220 m extrusions.
  const h = 12 + Math.log10(Math.max(valueKes, 1e5) / 1e5) * 55;
  return Math.min(220, Math.max(12, h));
}

function colorForPoint(p: PortfolioPoint, mode: MapMode): string {
  if (mode === "quality") {
    if (p.confidence === "high") return "#86efac";
    if (p.confidence === "medium") return "#fde68a";
    return "#fca5a5";
  }
  // Portfolio / capital still encode TIV height; colour still shows flood risk.
  const score = floodRiskScore({
    hazard_severe: p.hazard_severe,
    depth: p.depth,
    value_kes: p.value_kes,
    loss_kes: p.loss_kes,
  });
  return colorForFloodRisk(score);
}

function squareAround(lon: number, lat: number, half = FOOTPRINT): GeoJSON.Polygon {
  return {
    type: "Polygon",
    coordinates: [
      [
        [lon - half, lat - half],
        [lon + half, lat - half],
        [lon + half, lat + half],
        [lon - half, lat + half],
        [lon - half, lat - half],
      ],
    ],
  };
}

function pointsToExtrusions(
  points: PortfolioPoint[],
  mode: MapMode,
): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: points.map((p) => ({
      type: "Feature",
      properties: {
        id: p.id,
        height: heightFromTiv(p.value_kes),
        color: colorForPoint(p, mode),
        depth: p.depth,
        value_kes: p.value_kes,
        hazard_severe: p.hazard_severe,
        risk: floodRiskScore({
          hazard_severe: p.hazard_severe,
          depth: p.depth,
          value_kes: p.value_kes,
          loss_kes: p.loss_kes,
        }),
        insured: p.insured,
        confidence: p.confidence,
        selected: false,
      },
      geometry: squareAround(p.lon, p.lat),
    })),
  };
}

function pointsToHeat(points: PortfolioPoint[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: points
      .filter((p) => p.depth > 0.15)
      .map((p) => ({
        type: "Feature",
        properties: { depth: p.depth },
        geometry: { type: "Point", coordinates: [p.lon, p.lat] },
      })),
  };
}

function hotspotsToGeoJSON(hotspots: Hotspot[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: hotspots.map((h) => ({
      type: "Feature",
      properties: { name: h.name },
      geometry: { type: "Point", coordinates: [h.lon, h.lat] },
    })),
  };
}

function buildStyle(basemap: BasemapStyle): string | StyleSpecification {
  if (basemap === "satellite") {
    return {
      version: 8,
      sources: {
        esri: {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          attribution: "Tiles © Esri",
          maxzoom: 19,
        },
        labels: {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          maxzoom: 19,
        },
      },
      layers: [
        { id: "esri", type: "raster", source: "esri" },
        { id: "labels", type: "raster", source: "labels", paint: { "raster-opacity": 0.9 } },
      ],
      glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
    };
  }

  // OpenFreeMap Liberty includes OpenMapTiles vector layers (buildings, etc.).
  return "https://tiles.openfreemap.org/styles/liberty";
}

function ensurePortfolioLayers(map: MapLibreMap, mode: MapMode) {
  const showFlood =
    mode === "overview" || mode === "hazard" || mode === "loss" || mode === "risk";

  if (!map.getSource("portfolio")) {
    map.addSource("portfolio", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
  }
  if (!map.getSource("flood-heat")) {
    map.addSource("flood-heat", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
  }
  if (!map.getSource("hotspots")) {
    map.addSource("hotspots", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
  }

  // Contextual city fabric (streets style only).
  if (map.getSource("openmaptiles") && !map.getLayer("city-buildings")) {
    if (map.getLayer("building-3d")) {
      map.setPaintProperty("building-3d", "fill-extrusion-opacity", 0.25);
    }
    map.addLayer({
      id: "city-buildings",
      source: "openmaptiles",
      "source-layer": "building",
      type: "fill-extrusion",
      minzoom: 13,
      paint: {
        "fill-extrusion-color": "#1e3a5f",
        "fill-extrusion-height": ["coalesce", ["get", "render_height"], 8],
        "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
        "fill-extrusion-opacity": 0.35,
      },
    });
  }

  if (!map.getLayer("flood-heat")) {
    map.addLayer({
      id: "flood-heat",
      type: "heatmap",
      source: "flood-heat",
      layout: { visibility: showFlood ? "visible" : "none" },
      paint: {
        "heatmap-weight": [
          "interpolate",
          ["linear"],
          ["get", "depth"],
          0,
          0.05,
          3.2,
          1,
        ],
        "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 11, 22, 15, 55],
        "heatmap-intensity": 0.85,
        "heatmap-opacity": 0.55,
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(0,0,0,0)",
          0.15,
          "rgba(254,249,195,0.35)",
          0.35,
          "rgba(253,186,116,0.55)",
          0.55,
          "rgba(252,165,165,0.75)",
          0.75,
          "rgba(239,68,68,0.9)",
          1,
          "rgba(185,28,28,1)",
        ],
      },
    });
  } else {
    map.setLayoutProperty(
      "flood-heat",
      "visibility",
      showFlood ? "visible" : "none",
    );
  }

  if (!map.getLayer("portfolio-3d")) {
    map.addLayer({
      id: "portfolio-3d",
      type: "fill-extrusion",
      source: "portfolio",
      paint: {
        "fill-extrusion-color": ["get", "color"],
        "fill-extrusion-height": ["get", "height"],
        "fill-extrusion-base": 0,
        "fill-extrusion-opacity": 0.92,
      },
    });
  }

  if (!map.getLayer("portfolio-selected")) {
    map.addLayer({
      id: "portfolio-selected",
      type: "fill-extrusion",
      source: "portfolio",
      filter: ["==", ["get", "id"], ""],
      paint: {
        "fill-extrusion-color": "#f8fafc",
        "fill-extrusion-height": ["+", ["get", "height"], 8],
        "fill-extrusion-base": 0,
        "fill-extrusion-opacity": 1,
      },
    });
  }

  if (!map.getLayer("hotspot-halo")) {
    map.addLayer({
      id: "hotspot-halo",
      type: "circle",
      source: "hotspots",
      paint: {
        "circle-color": "#fb7185",
        "circle-radius": 14,
        "circle-opacity": 0.35,
        "circle-blur": 0.55,
      },
    });
  }

  if (!map.getLayer("hotspot-dots")) {
    map.addLayer({
      id: "hotspot-dots",
      type: "circle",
      source: "hotspots",
      paint: {
        "circle-color": "#fb7185",
        "circle-radius": 5,
        "circle-stroke-color": "#fff",
        "circle-stroke-width": 1.5,
      },
    });
  }

  if (!map.getLayer("hotspot-labels")) {
    map.addLayer({
      id: "hotspot-labels",
      type: "symbol",
      source: "hotspots",
      minzoom: 12.5,
      layout: {
        "text-field": ["get", "name"],
        "text-size": 11,
        "text-offset": [0, 1.2],
        "text-font": ["Noto Sans Regular"],
        "text-allow-overlap": false,
      },
      paint: {
        "text-color": "#fecdd3",
        "text-halo-color": "#020617",
        "text-halo-width": 1.5,
      },
    });
  }
}

function fitMapToPoints(map: MapLibreMap, points: PortfolioPoint[]) {
  const bounds = boundsFromPoints(points);
  if (!bounds) return;
  map.fitBounds(bounds, {
    padding: { top: 56, bottom: 56, left: 48, right: 120 },
    maxZoom: 14.8,
    pitch: 52,
    bearing: -12,
    duration: 900,
  });
}

export default function MapLibre3DInner({
  mode,
  basemap = "streets",
  points,
  hotspots,
  selectedId,
  onSelect,
  fitToData = true,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const dataRef = useRef({ points, hotspots, mode, selectedId, fitToData });
  dataRef.current = { points, hotspots, mode, selectedId, fitToData };
  const readyRef = useRef(false);
  const fittedKeyRef = useRef<string>("");
  const popupRef = useRef<maplibregl.Popup | null>(null);

  // Init / re-init when basemap changes (style swap).
  useEffect(() => {
    if (!containerRef.current) return;

    let cancelled = false;
    let map: MapLibreMap | null = null;
    let raf = 0;
    fittedKeyRef.current = "";

    const seed = dataRef.current.points[0];
    const center: [number, number] = seed
      ? [seed.lon, seed.lat]
      : KENYA_FALLBACK;

    try {
      if (typeof window !== "undefined") {
        maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");
      }
      map = new maplibregl.Map({
        container: containerRef.current,
        style: buildStyle(basemap),
        center,
        zoom: 12.5,
        pitch: 52,
        bearing: -12,
        maxPitch: 75,
        minZoom: 2,
        maxZoom: 18,
        // No city lock — camera follows whatever portfolio was uploaded.
        attributionControl: { compact: true },
      });
    } catch (err) {
      console.warn("MapLibre WebGL init failed:", err);
      return;
    }

    mapRef.current = map;
    map.addControl(
      new maplibregl.NavigationControl({ visualizePitch: true, showCompass: true }),
      "top-left",
    );
    map.dragRotate.enable();
    map.touchZoomRotate.enableRotation();

    popupRef.current = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 12,
      className: "ft-map-popup",
      maxWidth: "240px",
    });

    const onClick = (e: MapLayerMouseEvent) => {
      const hit = e.features?.[0];
      const id = hit?.properties?.id as string | undefined;
      if (id) onSelectRef.current(id);
    };

    const onMove = (e: MapLayerMouseEvent) => {
      if (!map) return;
      map.getCanvas().style.cursor = e.features?.length ? "pointer" : "";
      const hit = e.features?.[0];
      if (!hit || !popupRef.current) {
        popupRef.current?.remove();
        return;
      }
      const props = hit.properties ?? {};
      const value = Number(props.value_kes ?? 0);
      const depth = Number(props.depth ?? 0);
      const risk = Number(props.risk ?? 0);
      const label = props.insured ? "Insured" : "Uninsured";
      const riskLabel =
        risk >= 0.72
          ? "Extreme"
          : risk >= 0.5
            ? "High"
            : risk >= 0.32
              ? "Moderate"
              : risk >= 0.15
                ? "Low"
                : "Very low";
      popupRef.current
        .setLngLat(e.lngLat)
        .setHTML(
          `<strong>${props.id}</strong><br/>${label} · flood risk ${riskLabel}<br/>Depth ~ ${depth.toFixed(1)} m · TIV ${(value / 1e6).toFixed(1)}M KES`,
        )
        .addTo(map);
    };

    const onLeave = () => {
      if (!map) return;
      map.getCanvas().style.cursor = "";
      popupRef.current?.remove();
    };

    map.on("load", () => {
      if (cancelled || !map) return;
      const snapshot = dataRef.current;
      ensurePortfolioLayers(map, snapshot.mode);
      readyRef.current = true;

      const pulse = (t: number) => {
        if (!map || cancelled) return;
        const k = (Math.sin(t / 400) + 1) / 2;
        if (map.getLayer("hotspot-halo")) {
          map.setPaintProperty("hotspot-halo", "circle-radius", 10 + k * 10);
          map.setPaintProperty("hotspot-halo", "circle-opacity", 0.45 - k * 0.28);
        }
        raf = requestAnimationFrame(pulse);
      };
      raf = requestAnimationFrame(pulse);

      map.on("click", "portfolio-3d", onClick);
      map.on("mousemove", "portfolio-3d", onMove);
      map.on("mouseleave", "portfolio-3d", onLeave);

      const portfolioSrc = map.getSource("portfolio") as GeoJSONSource | undefined;
      const heatSrc = map.getSource("flood-heat") as GeoJSONSource | undefined;
      const hsSrc = map.getSource("hotspots") as GeoJSONSource | undefined;
      portfolioSrc?.setData(
        pointsToExtrusions(snapshot.points, snapshot.mode) as GeoJSON.GeoJSON,
      );
      heatSrc?.setData(pointsToHeat(snapshot.points) as GeoJSON.GeoJSON);
      hsSrc?.setData(hotspotsToGeoJSON(snapshot.hotspots) as GeoJSON.GeoJSON);
      if (snapshot.selectedId && map.getLayer("portfolio-selected")) {
        map.setFilter("portfolio-selected", [
          "==",
          ["get", "id"],
          snapshot.selectedId,
        ]);
      }
      if (snapshot.fitToData && snapshot.points.length) {
        const key = `${snapshot.points.length}:${snapshot.points[0]?.id}:${snapshot.points[snapshot.points.length - 1]?.id}`;
        fittedKeyRef.current = key;
        fitMapToPoints(map, snapshot.points);
      }
    });

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      readyRef.current = false;
      popupRef.current?.remove();
      map?.remove();
      mapRef.current = null;
    };
  }, [basemap]);

  // Sync portfolio / heat / hotspots when data or mode changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;

    const apply = () => {
      ensurePortfolioLayers(map, mode);
      const portfolioSrc = map.getSource("portfolio") as GeoJSONSource | undefined;
      const heatSrc = map.getSource("flood-heat") as GeoJSONSource | undefined;
      const hsSrc = map.getSource("hotspots") as GeoJSONSource | undefined;
      portfolioSrc?.setData(pointsToExtrusions(points, mode) as GeoJSON.GeoJSON);
      heatSrc?.setData(pointsToHeat(points) as GeoJSON.GeoJSON);
      hsSrc?.setData(hotspotsToGeoJSON(hotspots) as GeoJSON.GeoJSON);

      const intensity =
        0.35 +
        Math.min(
          1,
          points.reduce((s, p) => s + p.depth, 0) / (points.length * 2.5 || 1),
        ) *
          1.4;
      if (map.getLayer("flood-heat")) {
        map.setPaintProperty("flood-heat", "heatmap-intensity", intensity);
      }

      if (fitToData && points.length) {
        const key = `${points.length}:${points[0]?.id}:${points[points.length - 1]?.id}`;
        if (fittedKeyRef.current !== key) {
          fittedKeyRef.current = key;
          fitMapToPoints(map, points);
        }
      }
    };

    if (map.isStyleLoaded()) apply();
    else map.once("idle", apply);
  }, [points, hotspots, mode, fitToData]);

  // Highlight selection + fly to property.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current || !map.getLayer("portfolio-selected")) return;
    map.setFilter(
      "portfolio-selected",
      selectedId ? ["==", ["get", "id"], selectedId] : ["==", ["get", "id"], ""],
    );
    if (!selectedId) return;
    const pt = points.find((p) => p.id === selectedId);
    if (!pt) return;
    map.easeTo({
      center: [pt.lon, pt.lat],
      zoom: Math.max(map.getZoom(), 14.5),
      pitch: 62,
      duration: 700,
    });
  }, [selectedId, points]);

  return <div ref={containerRef} className="h-full w-full" />;
}
