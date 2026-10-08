'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Map as MaplibreMap, Marker, Popup, NavigationControl } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import styles from './dashboard.module.css';

// ===================================================================
// NAIROBI REAL GEOGRAPHIC DATA (Coordinates, Rivers, Risks & Hotspots)
// ===================================================================

// Insured Commercial Risks in Nairobi Metropolitan Basin
const NAIROBI_INSURED_PROPERTIES = [
  {
    id: 'KE-NRB-001',
    name: 'Kenya Re Headquarters (Reinsurance Plaza)',
    lat: -1.2875,
    lng: 36.8236,
    address: 'Taifa Rd / Aga Khan Walk, Nairobi CBD',
    tiv: 'KES 850,000,000',
    assetType: 'Commercial Headquarters / High-Rise',
    elevation: '1,675 m',
    floodDepthBase: 0.15,
    status: 'OPTIMAL',
    recommendation: 'Elevation profile mitigated; standard deductible applies.',
  },
  {
    id: 'KE-NRB-002',
    name: 'Industrial Area Central Manufacturing Depot',
    lat: -1.3120,
    lng: 36.8520,
    address: 'Enterprise Rd / Commercial St, Industrial Area',
    tiv: 'KES 420,000,000',
    assetType: 'Heavy Industrial / Warehouse Storage',
    elevation: '1,642 m',
    floodDepthBase: 2.45,
    status: 'CRITICAL_TAIL',
    recommendation: 'Ngong River confluence bottleneck. Enforce 15% inundation sub-limit.',
  },
  {
    id: 'KE-NRB-003',
    name: 'Sameer Business Park Logistics Hub',
    lat: -1.3240,
    lng: 36.8580,
    address: 'Mombasa Road Corridor, Nairobi',
    tiv: 'KES 680,000,000',
    assetType: 'Commercial Office & Light Logistics',
    elevation: '1,646 m',
    floodDepthBase: 1.85,
    status: 'ELEVATED',
    recommendation: 'Pluvial overland flow zone; bunding & sump pumps required.',
  },
  {
    id: 'KE-NRB-004',
    name: 'Upper Hill Financial District Complex',
    lat: -1.2990,
    lng: 36.8140,
    address: 'Hospital Rd / Kilimanjaro Ave, Upper Hill',
    tiv: 'KES 540,000,000',
    assetType: 'Financial Services Towers',
    elevation: '1,720 m',
    floodDepthBase: 0.05,
    status: 'OPTIMAL',
    recommendation: 'Ridge topography; zero riverine flood susceptibility.',
  },
  {
    id: 'KE-NRB-005',
    name: 'Westlands Commercial Hub (The Oval)',
    lat: -1.2640,
    lng: 36.8040,
    address: 'Waiyaki Way / Ring Rd Westlands',
    tiv: 'KES 380,000,000',
    assetType: 'Retail & Premium Commercial Office',
    elevation: '1,710 m',
    floodDepthBase: 0.10,
    status: 'OPTIMAL',
    recommendation: 'Well-drained ridge; basement water ingress seals inspected.',
  },
  {
    id: 'KE-NRB-006',
    name: 'South C Distribution & Cold Storage Facility',
    lat: -1.3180,
    lng: 36.8310,
    address: 'Muhoho Ave, South C / Bellevue',
    tiv: 'KES 290,000,000',
    assetType: 'Cold Storage & FMCG Distribution',
    elevation: '1,648 m',
    floodDepthBase: 2.10,
    status: 'CRITICAL_TAIL',
    recommendation: 'Pluvial drainage surcharge zone; cargo elevation to 1.2m mandatory.',
  },
  {
    id: 'KE-NRB-007',
    name: 'Embakasi Inland Container Depot (ICD) Terminal',
    lat: -1.3350,
    lng: 36.8920,
    address: 'Airport North Rd, Embakasi',
    tiv: 'KES 310,000,000',
    assetType: 'Container Yard & Rail Intermodal Freight',
    elevation: '1,620 m',
    floodDepthBase: 1.40,
    status: 'MODERATE',
    recommendation: 'Surface runoff drainage basin; verify retention basin clearance.',
  },
  {
    id: 'KE-NRB-008',
    name: 'Ruaraka Light Manufacturing Hub',
    lat: -1.2460,
    lng: 36.8820,
    address: 'Baba Dogo Rd, Ruaraka Industrial Belt',
    tiv: 'KES 260,000,000',
    assetType: 'Consumer Goods Manufacturing',
    elevation: '1,605 m',
    floodDepthBase: 1.20,
    status: 'MODERATE',
    recommendation: 'Ruaraka River tributary buffer; periodic clearing of culverts required.',
  },
];

// Uninsured Building Hotspots in Nairobi Low-Lying Drainage Basins
const NAIROBI_UNINSURED_HOTSPOTS = [
  { lat: -1.2610, lng: 36.8580, label: 'Mathare 4A Riverbank Zone' },
  { lat: -1.2645, lng: 36.8640, label: 'Huruma Drainage Surcharge' },
  { lat: -1.3140, lng: 36.7920, label: 'Kibera Ngong River Corridor' },
  { lat: -1.3160, lng: 36.7980, label: 'Nairobi Dam Lowland Flats' },
  { lat: -1.3175, lng: 36.8680, label: 'Mukuru Kwa Njenga Industrial Basin' },
  { lat: -1.3200, lng: 36.8740, label: 'Mukuru Kayaba River Bend' },
  { lat: -1.2820, lng: 36.8420, label: 'Gikomba Market Flood Zone' },
  { lat: -1.2520, lng: 36.8910, label: 'Korogocho Lowland Silt Basin' },
];

// Pulsing Accumulation Hotspots (Critical Tail Concentrations)
const ACCUMULATION_HOTSPOTS = [
  {
    lat: -1.3120,
    lng: 36.8520,
    name: 'Nairobi Industrial Tail Concentration Hotspot',
    basin: 'Ngong River / Enterprise Corridor',
    tiv: 'KES 142.5M',
    peakDepth: '2.45 m',
  },
  {
    lat: -1.3180,
    lng: 36.8310,
    name: 'South C / Nairobi West Pluvial Accumulation Hotspot',
    basin: 'Muhoho Ave Drainage Surcharge',
    tiv: 'KES 68.4M',
    peakDepth: '2.10 m',
  },
  {
    lat: -1.2620,
    lng: 36.8580,
    name: 'Mathare Valley Riverine Flash Inundation Hotspot',
    basin: 'Mathare River Tributary Bend',
    tiv: 'KES 34.2M',
    peakDepth: '2.80 m',
  },
];

// River Trajectories (Real Nairobi River & Ngong River channels)
const NAIROBI_RIVER_CHANNEL = [
  [36.7820, -1.2550],
  [36.8040, -1.2620],
  [36.8200, -1.2710],
  [36.8380, -1.2780],
  [36.8510, -1.2810],
  [36.8680, -1.2740],
  [36.8920, -1.2680],
  [36.9200, -1.2620],
  [36.9600, -1.2550],
];

const NGONG_RIVER_CHANNEL = [
  [36.7550, -1.3250],
  [36.7850, -1.3180],
  [36.8050, -1.3150],
  [36.8300, -1.3170],
  [36.8550, -1.3130],
  [36.8780, -1.3200],
  [36.9100, -1.3280],
  [36.9450, -1.3210],
];

const MATHARE_RIVER_CHANNEL = [
  [36.8200, -1.2480],
  [36.8400, -1.2540],
  [36.8580, -1.2610],
  [36.8780, -1.2650],
  [36.8950, -1.2700],
];

// Flood inundation zone polygons (circles approximated as GeoJSON polygons)
function createCirclePolygon(center, radiusKm, numPoints = 48) {
  const coords = [];
  const lat = center[1];
  const lng = center[0];
  for (let i = 0; i <= numPoints; i++) {
    const angle = (i / numPoints) * 2 * Math.PI;
    const dx = radiusKm * Math.cos(angle);
    const dy = radiusKm * Math.sin(angle);
    // Approximate: 1 degree latitude ≈ 111km, 1 degree longitude ≈ 111km * cos(lat)
    const dLat = dy / 111;
    const dLng = dx / (111 * Math.cos((lat * Math.PI) / 180));
    coords.push([lng + dLng, lat + dLat]);
  }
  return [coords];
}

export default function NairobiRealMap({
  rainfallMm = 85,
  mapFilter = 'insured',
  onSelectProperty,
}) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const popupRef = useRef(null);
  const markersRef = useRef([]);
  const [isMapReady, setIsMapReady] = useState(false);
  const [basemapType, setBasemapType] = useState('dark');
  const [viewScope, setViewScope] = useState('nairobi');

  // Cleanup markers
  const clearMarkers = useCallback(() => {
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];
  }, []);

  // Initialize MapLibre GL map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center: [36.8219, -1.2921], // Nairobi
      zoom: 12,
      pitch: 45,
      bearing: -17.6,
      antialias: true,
      attributionControl: false,
    });

    mapRef.current = map;

    map.on('load', () => {
      // Add 3D buildings layer from OpenFreeMap vector tiles
      const layers = map.getStyle().layers;
      // Find the label layer to insert 3D buildings before it
      let labelLayerId;
      for (let i = 0; i < layers.length; i++) {
        if (layers[i].type === 'symbol' && layers[i].layout && layers[i].layout['text-field']) {
          labelLayerId = layers[i].id;
          break;
        }
      }

      // Check if building source exists from the style
      const sources = map.getStyle().sources;
      const hasBuildings = Object.keys(sources).some(
        (s) => s === 'openmaptiles' || s === 'openfreemap'
      );

      if (hasBuildings) {
        // Add 3D building extrusions
        // Try to add the layer — it may already exist in some styles
        try {
          map.addLayer(
            {
              id: '3d-buildings',
              source: Object.keys(sources).find(
                (s) => s === 'openmaptiles' || s === 'openfreemap'
              ),
              'source-layer': 'building',
              type: 'fill-extrusion',
              minzoom: 13,
              paint: {
                'fill-extrusion-color': [
                  'interpolate',
                  ['linear'],
                  ['get', 'render_height'],
                  0, '#0a1628',
                  15, '#0d2847',
                  30, '#1a3a5c',
                  60, '#2a5080',
                ],
                'fill-extrusion-height': [
                  'interpolate',
                  ['linear'],
                  ['zoom'],
                  13, 0,
                  14, ['get', 'render_height'],
                ],
                'fill-extrusion-base': [
                  'interpolate',
                  ['linear'],
                  ['zoom'],
                  13, 0,
                  14, ['get', 'render_min_height'],
                ],
                'fill-extrusion-opacity': 0.75,
              },
            },
            labelLayerId
          );
        } catch (e) {
          // Layer may already exist in style
          console.log('3D buildings layer setup note:', e.message);
        }
      }

      // ---------------------------------------------------------------
      // River corridors as GeoJSON line sources
      // ---------------------------------------------------------------
      map.addSource('nairobi-river', {
        type: 'geojson',
        data: {
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: NAIROBI_RIVER_CHANNEL },
          properties: { name: 'Nairobi River Corridor (Main Trunk)' },
        },
      });
      map.addLayer({
        id: 'nairobi-river-line',
        type: 'line',
        source: 'nairobi-river',
        paint: {
          'line-color': '#00E5FF',
          'line-width': 3.5,
          'line-opacity': 0.85,
        },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      });
      // River glow
      map.addLayer({
        id: 'nairobi-river-glow',
        type: 'line',
        source: 'nairobi-river',
        paint: {
          'line-color': '#00E5FF',
          'line-width': 10,
          'line-opacity': 0.15,
          'line-blur': 8,
        },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      });

      map.addSource('ngong-river', {
        type: 'geojson',
        data: {
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: NGONG_RIVER_CHANNEL },
          properties: { name: 'Ngong River Channel' },
        },
      });
      map.addLayer({
        id: 'ngong-river-line',
        type: 'line',
        source: 'ngong-river',
        paint: {
          'line-color': '#0284c7',
          'line-width': 4,
          'line-opacity': 0.85,
        },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      });
      map.addLayer({
        id: 'ngong-river-glow',
        type: 'line',
        source: 'ngong-river',
        paint: {
          'line-color': '#0284c7',
          'line-width': 12,
          'line-opacity': 0.12,
          'line-blur': 8,
        },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      });

      map.addSource('mathare-river', {
        type: 'geojson',
        data: {
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: MATHARE_RIVER_CHANNEL },
          properties: { name: 'Mathare River Flash Corridor' },
        },
      });
      map.addLayer({
        id: 'mathare-river-line',
        type: 'line',
        source: 'mathare-river',
        paint: {
          'line-color': '#38bdf8',
          'line-width': 2.5,
          'line-opacity': 0.85,
        },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      });

      setIsMapReady(true);
    });

    // Cleanup
    return () => {
      clearMarkers();
      if (popupRef.current) popupRef.current.remove();
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [clearMarkers]);

  // Update flood inundation zones when rainfall changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapReady) return;

    const rainScale = rainfallMm / 100;

    // Define inundation zones
    const floodZones = [
      {
        id: 'flood-zone-industrial',
        center: [36.8520, -1.3120],
        radiusKm: (0.68 + rainScale * 0.4),
        color: '#1e1b4b',
        opacity: Math.min(0.55 + rainScale * 0.35, 0.9),
      },
      {
        id: 'flood-zone-southc',
        center: [36.8310, -1.3180],
        radiusKm: (0.52 + rainScale * 0.35),
        color: '#1d4ed8',
        opacity: Math.min(0.5 + rainScale * 0.3, 0.85),
      },
      {
        id: 'flood-zone-mathare',
        center: [36.8580, -1.2620],
        radiusKm: (0.42 + rainScale * 0.28),
        color: '#0284c7',
        opacity: Math.min(0.45 + rainScale * 0.25, 0.8),
      },
      {
        id: 'flood-zone-embakasi',
        center: [36.8920, -1.3350],
        radiusKm: (0.60 + rainScale * 0.32),
        color: '#0284c7',
        opacity: 0.45,
      },
      {
        id: 'flood-zone-gikomba',
        center: [36.8420, -1.2820],
        radiusKm: (0.35 + rainScale * 0.20),
        color: '#38bdf8',
        opacity: 0.4,
      },
    ];

    floodZones.forEach((zone) => {
      const sourceId = `${zone.id}-src`;
      const layerId = `${zone.id}-fill`;

      const geojsonData = {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: createCirclePolygon(zone.center, zone.radiusKm),
        },
        properties: {},
      };

      if (map.getSource(sourceId)) {
        map.getSource(sourceId).setData(geojsonData);
        map.setPaintProperty(layerId, 'fill-opacity', zone.opacity);
      } else {
        map.addSource(sourceId, { type: 'geojson', data: geojsonData });
        map.addLayer(
          {
            id: layerId,
            type: 'fill',
            source: sourceId,
            paint: {
              'fill-color': zone.color,
              'fill-opacity': zone.opacity,
            },
          },
          'nairobi-river-glow' // Insert below rivers
        );
      }
    });
  }, [rainfallMm, isMapReady]);

  // Update markers when filter or rainfall changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapReady) return;

    clearMarkers();

    const rainScale = rainfallMm / 100;

    // Accumulation Hotspots (red pulsing markers)
    ACCUMULATION_HOTSPOTS.forEach((spot) => {
      const el = document.createElement('div');
      el.className = 'maplibre-hotspot-marker';
      el.innerHTML = `
        <div style="
          width: 24px; height: 24px; border-radius: 50%;
          background: radial-gradient(circle, #ef4444 40%, rgba(239,68,68,0.3) 100%);
          border: 2px solid #ffffff;
          box-shadow: 0 0 12px rgba(239,68,68,0.6), 0 0 24px rgba(239,68,68,0.3);
          animation: hotspotPulse 2s ease-in-out infinite;
          cursor: pointer;
        "></div>
      `;

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([spot.lng, spot.lat])
        .setPopup(
          new maplibregl.Popup({ offset: 16, className: 'floodtail-popup' }).setHTML(`
            <div style="font-family: system-ui, sans-serif; color: #ffffff; padding: 6px; max-width: 260px;">
              <div style="font-size: 11px; font-weight: 800; color: #ef4444; letter-spacing: 0.5px; text-transform: uppercase;">
                ⚠️ ACCUMULATION HOTSPOT
              </div>
              <div style="font-size: 14px; font-weight: 800; margin: 6px 0 3px 0;">
                ${spot.name}
              </div>
              <div style="font-size: 11.5px; color: #94A3B8; margin-bottom: 8px;">
                Basin: ${spot.basin}
              </div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px; background: rgba(0,0,0,0.4); padding: 8px; border-radius: 6px;">
                <div>TIV at Risk: <strong style="color: #00E5FF;">${spot.tiv}</strong></div>
                <div>Peak Depth: <strong style="color: #ef4444;">${spot.peakDepth}</strong></div>
              </div>
            </div>
          `)
        )
        .addTo(map);

      markersRef.current.push(marker);
    });

    // Insured Properties (cyan markers)
    NAIROBI_INSURED_PROPERTIES.forEach((prop) => {
      const dynamicDepth = (prop.floodDepthBase * rainScale).toFixed(2);

      const el = document.createElement('div');
      el.style.cssText = `
        width: 14px; height: 14px; border-radius: 50%;
        background: #00E5FF;
        border: 2px solid #ffffff;
        box-shadow: 0 0 8px rgba(0,229,255,0.5);
        cursor: pointer;
        transition: transform 0.2s;
      `;
      el.addEventListener('mouseenter', () => { el.style.transform = 'scale(1.4)'; });
      el.addEventListener('mouseleave', () => { el.style.transform = 'scale(1)'; });

      const statusColor = prop.status === 'CRITICAL_TAIL' ? '#ef4444' : prop.status === 'ELEVATED' ? '#f59e0b' : '#10b981';
      const statusBg = prop.status === 'CRITICAL_TAIL' ? 'rgba(239,68,68,0.2)' : prop.status === 'ELEVATED' ? 'rgba(245,158,11,0.2)' : 'rgba(16,185,129,0.2)';

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([prop.lng, prop.lat])
        .setPopup(
          new maplibregl.Popup({ offset: 12, className: 'floodtail-popup' }).setHTML(`
            <div style="font-family: system-ui, sans-serif; color: #ffffff; min-width: 240px; padding: 6px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 10px; font-weight: 800; color: #00E5FF; letter-spacing: 0.5px;">INSURED PROPERTY</span>
                <span style="font-size: 9.5px; padding: 2px 6px; border-radius: 4px; background: ${statusBg}; color: ${statusColor}; font-weight: 700;">${prop.status}</span>
              </div>
              <div style="font-size: 13.5px; font-weight: 800; line-height: 1.25; margin-bottom: 2px;">
                ${prop.name}
              </div>
              <div style="font-size: 11px; color: #94A3B8; margin-bottom: 8px;">
                📍 ${prop.address}
              </div>
              <div style="background: rgba(2,6,16,0.6); border: 1px solid rgba(0,229,255,0.2); border-radius: 6px; padding: 8px; font-size: 11px; display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 8px;">
                <div>TIV: <strong style="color: #ffffff;">${prop.tiv}</strong></div>
                <div>Elevation: <strong style="color: #ffffff;">${prop.elevation}</strong></div>
                <div>Flood Depth: <strong style="color: ${dynamicDepth > 1.0 ? '#ef4444' : '#00E5FF'};">${dynamicDepth} m</strong></div>
                <div>Policy ID: <strong style="color: #94A3B8;">${prop.id}</strong></div>
              </div>
              <div style="font-size: 10.5px; color: #CBD5E1; line-height: 1.35; border-left: 2px solid #00E5FF; padding-left: 6px;">
                <strong>Underwriting Guidance:</strong> ${prop.recommendation}
              </div>
            </div>
          `)
        )
        .addTo(map);

      markersRef.current.push(marker);
    });

    // Uninsured Buildings (amber markers if toggled to "all")
    if (mapFilter === 'all') {
      NAIROBI_UNINSURED_HOTSPOTS.forEach((spot) => {
        const el = document.createElement('div');
        el.style.cssText = `
          width: 10px; height: 10px; border-radius: 50%;
          background: #f59e0b;
          border: 1.5px solid #000000;
          box-shadow: 0 0 6px rgba(245,158,11,0.4);
          cursor: pointer;
        `;

        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([spot.lng, spot.lat])
          .setPopup(
            new maplibregl.Popup({ offset: 8, className: 'floodtail-popup' }).setHTML(`
              <div style="font-family: system-ui, sans-serif; color: #ffffff; padding: 4px;">
                <div style="font-size: 10px; font-weight: 700; color: #f59e0b; text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 2px;">
                  Uninsured Settlement
                </div>
                <div style="font-size: 13px; font-weight: 600;">${spot.label}</div>
              </div>
            `)
          )
          .addTo(map);

        markersRef.current.push(marker);
      });
    }
  }, [rainfallMm, mapFilter, isMapReady, clearMarkers]);

  // Handle zoom
  const handleZoomIn = () => {
    if (mapRef.current) mapRef.current.zoomIn();
  };
  const handleZoomOut = () => {
    if (mapRef.current) mapRef.current.zoomOut();
  };

  // Toggle view scope
  const handleToggleScope = (scope) => {
    setViewScope(scope);
    if (!mapRef.current) return;
    if (scope === 'nairobi') {
      mapRef.current.flyTo({ center: [36.8219, -1.2921], zoom: 12, pitch: 45, bearing: -17.6, duration: 1500 });
    } else {
      mapRef.current.flyTo({ center: [37.9062, -0.0236], zoom: 6.5, pitch: 0, bearing: 0, duration: 1500 });
    }
  };

  // Toggle basemap
  const handleToggleBasemap = () => {
    if (!mapRef.current) return;
    const map = mapRef.current;
    const newType = basemapType === 'dark' ? 'satellite' : 'dark';
    setBasemapType(newType);

    // OpenFreeMap only offers vector styles, so we fake "satellite" by darkening
    // the map and changing building colors. For a true satellite, we'd need
    // a raster source, but we keep it free/no-API-key.
    if (newType === 'satellite') {
      // Darken the background for a "satellite-like" feel
      try {
        map.setPaintProperty('background', 'background-color', '#0a1220');
      } catch (e) { /* layer may not exist */ }
      // Make buildings more translucent
      try {
        map.setPaintProperty('3d-buildings', 'fill-extrusion-color', '#1a2a40');
        map.setPaintProperty('3d-buildings', 'fill-extrusion-opacity', 0.9);
      } catch (e) { /* layer may not exist */ }
    } else {
      try {
        map.setPaintProperty('background', 'background-color', '#f8f4f0');
      } catch (e) { /* layer may not exist */ }
      try {
        map.setPaintProperty('3d-buildings', 'fill-extrusion-color', [
          'interpolate', ['linear'], ['get', 'render_height'],
          0, '#0a1628', 15, '#0d2847', 30, '#1a3a5c', 60, '#2a5080',
        ]);
        map.setPaintProperty('3d-buildings', 'fill-extrusion-opacity', 0.75);
      } catch (e) { /* layer may not exist */ }
    }
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Map Container */}
      <div
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: '100%',
          background: '#020712',
          zIndex: 1,
        }}
      />

      {/* Top Left Controls */}
      <div
        style={{
          position: 'absolute',
          top: '12px',
          left: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          zIndex: 1000,
        }}
      >
        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            type="button"
            className={styles.mapControlBtn}
            onClick={handleZoomIn}
            title="Zoom In"
          >
            +
          </button>
          <button
            type="button"
            className={styles.mapControlBtn}
            onClick={handleZoomOut}
            title="Zoom Out"
          >
            −
          </button>
        </div>

        {/* Basemap Toggle */}
        <button
          type="button"
          onClick={handleToggleBasemap}
          style={{
            padding: '5px 10px',
            borderRadius: '6px',
            background: 'rgba(6, 16, 36, 0.9)',
            border: '1px solid rgba(0, 229, 255, 0.35)',
            color: '#00E5FF',
            fontSize: '11px',
            fontWeight: '700',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backdropFilter: 'blur(8px)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          }}
          title="Toggle Basemap Style"
        >
          <span>🛰️</span>
          <span>{basemapType === 'dark' ? 'Dark View' : 'Standard View'}</span>
        </button>

        {/* Scope Toggle */}
        <button
          type="button"
          onClick={() => handleToggleScope(viewScope === 'nairobi' ? 'kenya' : 'nairobi')}
          style={{
            padding: '5px 10px',
            borderRadius: '6px',
            background: 'rgba(6, 16, 36, 0.9)',
            border: '1px solid rgba(0, 229, 255, 0.35)',
            color: '#ffffff',
            fontSize: '11px',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backdropFilter: 'blur(8px)',
          }}
        >
          <span>📍</span>
          <span>{viewScope === 'nairobi' ? 'Nairobi City Basin' : 'Kenya Overview'}</span>
        </button>

        {/* 3D Toggle */}
        <button
          type="button"
          onClick={() => {
            if (!mapRef.current) return;
            const map = mapRef.current;
            const currentPitch = map.getPitch();
            if (currentPitch > 10) {
              map.easeTo({ pitch: 0, bearing: 0, duration: 800 });
            } else {
              map.easeTo({ pitch: 55, bearing: -17.6, duration: 800 });
            }
          }}
          style={{
            padding: '5px 10px',
            borderRadius: '6px',
            background: 'rgba(6, 16, 36, 0.9)',
            border: '1px solid rgba(0, 229, 255, 0.35)',
            color: '#00E5FF',
            fontSize: '11px',
            fontWeight: '700',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backdropFilter: 'blur(8px)',
          }}
          title="Toggle 3D View"
        >
          <span>🏗️</span>
          <span>3D Buildings</span>
        </button>
      </div>

      {/* Top Right Geographic Coordinate Pill */}
      <div
        style={{
          position: 'absolute',
          top: '12px',
          right: '180px',
          background: 'rgba(4, 12, 28, 0.85)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(0, 229, 255, 0.25)',
          borderRadius: '20px',
          padding: '4px 12px',
          fontSize: '10.5px',
          color: '#CBD5E1',
          zIndex: 999,
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}
      >
        <span style={{ color: '#00E5FF' }}>●</span>
        <span>Nairobi Basin: 1.2921° S, 36.8219° E</span>
      </div>

      {/* Pulse animation style */}
      <style>{`
        @keyframes hotspotPulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.3); opacity: 0.7; }
        }
        .maplibregl-popup-content {
          background: rgba(6, 16, 36, 0.95) !important;
          border: 1px solid rgba(0, 229, 255, 0.3) !important;
          border-radius: 10px !important;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6) !important;
          padding: 10px !important;
          color: #ffffff !important;
          backdrop-filter: blur(12px) !important;
        }
        .maplibregl-popup-tip {
          border-top-color: rgba(6, 16, 36, 0.95) !important;
        }
        .maplibregl-popup-close-button {
          color: #94A3B8 !important;
          font-size: 18px !important;
          padding: 4px 8px !important;
        }
        .maplibregl-popup-close-button:hover {
          color: #00E5FF !important;
          background: transparent !important;
        }
        .maplibregl-ctrl-attrib {
          display: none !important;
        }
      `}</style>
    </div>
  );
}
