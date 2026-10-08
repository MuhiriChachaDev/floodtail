"use client";
import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { Map } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type Status = "insured" | "uninsured" | "hotspot";
type Flag = { id: string; status: Status; lng: number; lat: number; height: number; geometry: any };

const COLORS: Record<Status, string> = { insured: "#22D3EE", uninsured: "#F5B921", hotspot: "#EF4444" };
const NAIROBI: [number, number] = [36.8219, -1.2921];

// Seeded random so the demo data is stable between reloads
function rng(seed: number) {
  return () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
}

// Demo flood-prone zones in Nairobi (lng, lat, spread, count)
const ZONES: [number, number, number, number][] = [
  [36.8560, -1.2830, 0.012, 60], // Mathare / Nairobi River
  [36.7870, -1.3130, 0.010, 50], // Kibera
  [36.8990, -1.3230, 0.016, 60], // Embakasi / Mukuru
  [36.8250, -1.2870, 0.008, 40], // CBD
  [36.8120, -1.2640, 0.010, 30], // Westlands / Ngong River
];

function buildDemoData() {
  const r = rng(42);
  const heat: any[] = [];
  const pts: any[] = [];
  ZONES.forEach(([lng, lat, s, n]) => {
    for (let i = 0; i < n; i++) {
      const x = lng + (r() - 0.5) * s * 2;
      const y = lat + (r() - 0.5) * s * 2;
      const depth = Math.max(0.2, 3.2 - Math.hypot(x - lng, y - lat) / s * 3);
      heat.push({ type: "Feature", properties: { depth }, geometry: { type: "Point", coordinates: [x, y] } });
      if (i % 3 === 0) {
        const t = r();
        const status: Status = depth > 2.4 ? "hotspot" : t > 0.45 ? "insured" : "uninsured";
        pts.push({ type: "Feature", properties: { status, color: COLORS[status] }, geometry: { type: "Point", coordinates: [x, y] } });
      }
    }
  });
  return {
    heat: { type: "FeatureCollection", features: heat },
    pts: { type: "FeatureCollection", features: pts },
  } as any;
}

const LABELS = [
  { n: "Nairobi CBD", c: [36.8219, -1.2864] }, { n: "Westlands", c: [36.8102, -1.2673] },
  { n: "Upper Hill", c: [36.8140, -1.2985] }, { n: "Kibera", c: [36.7870, -1.3130] },
  { n: "Eastleigh", c: [36.8500, -1.2750] }, { n: "Embakasi", c: [36.8990, -1.3230] },
];

function buildingId(g: any) {
  const p = g.type === "MultiPolygon" ? g.coordinates[0][0][0] : g.coordinates[0][0];
  return `${p[0].toFixed(5)}_${p[1].toFixed(5)}`;
}

export default function NairobiMap3D() {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const flags = useRef<Flag[]>([]);
  const [status, setStatus] = useState<Status>("insured");
  const statusRef = useRef(status);
  statusRef.current = status;
  const [count, setCount] = useState(0);
  const [rain, setRain] = useState(40);
  const [playing, setPlaying] = useState(false);
  const [insuredOnly, setInsuredOnly] = useState(false);
  const [ready, setReady] = useState(false);
  const [webGlError, setWebGlError] = useState(false);

  const syncFlags = () => {
    const src = mapRef.current?.getSource("flags") as maplibregl.GeoJSONSource | undefined;
    src?.setData({
      type: "FeatureCollection",
      features: flags.current.map((f) => ({
        type: "Feature", geometry: f.geometry,
        properties: { id: f.id, color: COLORS[f.status], height: f.height },
      })),
    } as any);
    setCount(flags.current.length);
  };

  const saveFlags = () =>
    fetch("/api/flags", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(flags.current) }).catch(() => {});

  // Init map
  useEffect(() => {
    if (typeof window !== "undefined") {
      maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");
    }

    let map: Map | null = null;
    try {
      map = new maplibregl.Map({
        container: el.current!,
        style: "https://tiles.openfreemap.org/styles/liberty",
        center: NAIROBI, zoom: 14.2, pitch: 58, bearing: -17,
        maxBounds: [[36.6, -1.45], [37.1, -1.1]], maxPitch: 80,
      });
      mapRef.current = map;
      map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-left");
    } catch (err) {
      console.warn("MapLibre GL WebGL2 initialization failed or not supported in this environment:", err);
      setWebGlError(true);
      return;
    }

    map.on("load", async () => {
      const demo = buildDemoData();

      // Replace default 3D buildings with ours (dark blue, themed)
      if (map.getLayer("building-3d")) map.removeLayer("building-3d");
      map.addLayer({
        id: "buildings-3d", source: "openmaptiles", "source-layer": "building",
        type: "fill-extrusion", minzoom: 13,
        paint: {
          "fill-extrusion-color": "#1e3a5f",
          "fill-extrusion-height": ["coalesce", ["get", "render_height"], 9],
          "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
          "fill-extrusion-opacity": 0.9,
        },
      });

      // Flood-depth heatmap (purple > blue > cyan)
      map.addSource("heat", { type: "geojson", data: demo.heat });
      map.addLayer({
        id: "flood-heat", type: "heatmap", source: "heat",
        paint: {
          "heatmap-weight": ["interpolate", ["linear"], ["get", "depth"], 0, 0.1, 3, 1],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 10, 18, 15, 60],
          "heatmap-intensity": 1,
          "heatmap-opacity": 0.6,
          "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"],
            0, "rgba(0,0,0,0)", 0.2, "rgba(34,211,238,0.5)", 0.45, "rgba(47,123,255,0.7)",
            0.7, "rgba(99,60,255,0.85)", 1, "rgba(139,92,246,1)"],
        },
      }, "buildings-3d");

      // Property markers
      map.addSource("pts", { type: "geojson", data: demo.pts });
      map.addLayer({
        id: "hotspot-halo", type: "circle", source: "pts", filter: ["==", ["get", "status"], "hotspot"],
        paint: { "circle-color": "#EF4444", "circle-radius": 10, "circle-opacity": 0.35, "circle-blur": 0.6 },
      });
      map.addLayer({
        id: "pts-dots", type: "circle", source: "pts",
        paint: {
          "circle-color": ["get", "color"], "circle-radius": 4.5,
          "circle-stroke-color": "#fff", "circle-stroke-width": 1,
        },
      });

      // User flags (3D highlighted buildings)
      map.addSource("flags", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "flags-3d", source: "flags", type: "fill-extrusion",
        paint: {
          "fill-extrusion-color": ["get", "color"],
          "fill-extrusion-height": ["+", ["get", "height"], 2],
          "fill-extrusion-base": 0, "fill-extrusion-opacity": 1,
        },
      });

      // Area labels
      map.addSource("labels", {
        type: "geojson",
        data: { type: "FeatureCollection", features: LABELS.map((l) => ({ type: "Feature", properties: { name: l.n }, geometry: { type: "Point", coordinates: l.c } })) } as any,
      });
      map.addLayer({
        id: "area-labels", type: "symbol", source: "labels",
        layout: { "text-field": ["get", "name"], "text-size": 14, "text-font": ["Noto Sans Regular"] },
        paint: { "text-color": "#fff", "text-halo-color": "#020617", "text-halo-width": 2 },
      });

      // Load saved flags
      try {
        const res = await fetch("/api/flags");
        flags.current = await res.json();
        syncFlags();
      } catch {}

      // Click to flag / unflag
      map.on("click", (e) => {
        const hit = map.queryRenderedFeatures(e.point, { layers: ["flags-3d", "buildings-3d"] })[0];
        if (!hit) return;
        const id = (hit.layer.id === "flags-3d" ? hit.properties?.id : buildingId(hit.geometry)) as string;
        const i = flags.current.findIndex((f) => f.id === id);
        if (i >= 0) {
          if (flags.current[i].status === statusRef.current) flags.current.splice(i, 1);
          else flags.current[i].status = statusRef.current;
        } else if (hit.layer.id === "buildings-3d") {
          flags.current.push({
            id, status: statusRef.current, lng: e.lngLat.lng, lat: e.lngLat.lat,
            height: Number(hit.properties?.render_height ?? 9), geometry: hit.geometry,
          });
        }
        syncFlags();
        saveFlags();
      });
      ["buildings-3d", "flags-3d"].forEach((l) => {
        map.on("mouseenter", l, () => (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", l, () => (map.getCanvas().style.cursor = ""));
      });

      // Pulsing hotspot halo
      let raf = 0;
      const pulse = (t: number) => {
        const k = (Math.sin(t / 400) + 1) / 2;
        if (map.getLayer("hotspot-halo")) {
          map.setPaintProperty("hotspot-halo", "circle-radius", 8 + k * 12);
          map.setPaintProperty("hotspot-halo", "circle-opacity", 0.5 - k * 0.35);
        }
        raf = requestAnimationFrame(pulse);
      };
      raf = requestAnimationFrame(pulse);
      map.once("remove", () => cancelAnimationFrame(raf));
      setReady(true);
    });

    return () => {
      if (map) map.remove();
    };
  }, []);

  // Rainfall slider drives heatmap
  useEffect(() => {
    const m = mapRef.current;
    if (!ready || !m) return;
    m.setPaintProperty("flood-heat", "heatmap-intensity", 0.3 + (rain / 100) * 1.7);
    m.setPaintProperty("flood-heat", "heatmap-opacity", 0.15 + (rain / 100) * 0.75);
  }, [rain, ready]);

  // Play button animates slider
  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => setRain((r) => (r >= 100 ? 0 : r + 2)), 120);
    return () => clearInterval(t);
  }, [playing]);

  // Insured / All buildings toggle
  useEffect(() => {
    const m = mapRef.current;
    if (!ready || !m) return;
    m.setFilter("pts-dots", insuredOnly ? ["==", ["get", "status"], "insured"] : null);
    m.setFilter("hotspot-halo", insuredOnly ? ["==", ["get", "status"], "none"] : ["==", ["get", "status"], "hotspot"]);
  }, [insuredOnly, ready]);

  return (
    <div className="relative h-[420px] w-full overflow-hidden rounded-xl border border-cyan-400/30">
      <div ref={el} className="absolute inset-0" />

      {webGlError && (
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: "url(/nairobi-landscape.jpg)",
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        >
          <div
            className="absolute inset-0"
            style={{
              background: "radial-gradient(ellipse at center, rgba(15,23,42,0.4) 0%, rgba(2,6,23,0.85) 100%)",
            }}
          />
          <div className="absolute top-3 left-3 flex items-center gap-2 rounded-lg border border-cyan-400/30 bg-slate-950/85 px-3 py-2 text-xs text-white backdrop-blur">
            <span className="text-cyan-300">●</span>
            <span>Nairobi Urban Basin · High-Res Satellite View (WebGL2 fallback active)</span>
          </div>
        </div>
      )}

      {/* Flag mode selector (top-left, below zoom controls) */}
      <div className="absolute left-3 top-28 flex flex-col gap-1 rounded-lg bg-slate-900/80 p-2 text-xs text-white backdrop-blur">
        <span className="text-[10px] uppercase tracking-wider text-slate-400">Flag as</span>
        {(["insured", "uninsured", "hotspot"] as const).map((s) => (
          <button key={s} onClick={() => setStatus(s)}
            className={`rounded px-2 py-1 text-left capitalize ${status === s ? "bg-white/20" : "hover:bg-white/10"}`}
            style={{ borderLeft: `3px solid ${COLORS[s]}` }}>{s}</button>
        ))}
        <span className="mt-1 text-[10px] text-slate-400">{count} flagged</span>
      </div>

      {/* Legend (top-right) */}
      <div className="absolute right-3 top-3 w-44 rounded-lg border border-white/10 bg-slate-950/85 p-3 text-[11px] text-slate-200 backdrop-blur">
        <p className="mb-2 font-medium">Flood Depth (m)</p>
        <div className="flex gap-2">
          <div className="h-24 w-2.5 rounded-sm bg-gradient-to-b from-violet-500 via-blue-500 to-cyan-400" />
          <div className="flex flex-col justify-between"><span>&gt; 3.0</span><span>2.0 – 3.0</span><span>1.0 – 2.0</span><span>0.5 – 1.0</span><span>&lt; 0.5</span></div>
        </div>
        <ul className="mt-3 space-y-1">
          {[["Insured Property", COLORS.insured], ["Uninsured Building", COLORS.uninsured], ["Accumulation Hotspot", COLORS.hotspot]].map(([t, c]) => (
            <li key={t} className="flex items-center gap-2"><i className="h-2 w-2 rounded-full" style={{ background: c }} />{t}</li>
          ))}
        </ul>
      </div>

      {/* Rainfall player (bottom-left) */}
      <div className="absolute bottom-3 left-3 flex w-72 items-center gap-3 rounded-xl border border-white/10 bg-slate-950/85 p-3 text-xs text-white backdrop-blur">
        <button onClick={() => setPlaying((p) => !p)} aria-label="Play rainfall simulation"
          className="grid h-9 w-9 place-items-center rounded-full border border-cyan-400 text-cyan-300">{playing ? "❚❚" : "▶"}</button>
        <div className="flex-1">
          <p className="mb-1">Rainfall (Next 24h)</p>
          <input type="range" min={0} max={100} value={rain} onChange={(e) => setRain(+e.target.value)} className="w-full accent-cyan-400" />
        </div>
      </div>

      {/* Insured / All Buildings toggle (bottom-right) */}
      <button onClick={() => setInsuredOnly((v) => !v)}
        className="absolute bottom-3 right-3 flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/85 px-3 py-2 text-xs text-white backdrop-blur">
        <span className={`h-4 w-8 rounded-full p-0.5 ${insuredOnly ? "bg-cyan-400" : "bg-slate-600"}`}>
          <span className={`block h-3 w-3 rounded-full bg-white transition ${insuredOnly ? "translate-x-4" : ""}`} />
        </span>
        {insuredOnly ? "Insured" : "All Buildings"}
      </button>
    </div>
  );
}
