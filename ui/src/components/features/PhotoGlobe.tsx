import { useRef, useState, useMemo, Suspense, useEffect } from 'react';
import { Canvas, useFrame, useLoader, useThree } from '@react-three/fiber';
import { OrbitControls, Stars, Html, Billboard } from '@react-three/drei';
import * as THREE from 'three';
import { Pause, Play, HelpCircle, Map as MapIcon } from 'lucide-react';
import { type Photo, api } from '../../api';
import { useAmbientThemeContext } from '../../contexts/AmbientThemeContext';
import SecureLazyImage from '../gallery/SecureLazyImage';

interface PhotoGlobeProps {
  photos: Photo[];
  onPhotoSelect: (photo: Photo) => void;
  onClose?: () => void;
  variant?: 'embedded' | 'fullscreen';
}

// Generate random GPS coordinates for photos without location
function parseCssAccentRgb(): THREE.Color {
  if (typeof window === 'undefined')
    return new THREE.Color('rgb(59, 130, 246)');
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue('--lm-accent-rgb')
    .trim();
  const parts = raw.split(/\s+/).map((p) => Number(p));
  if (parts.length >= 3 && parts.every((n) => Number.isFinite(n))) {
    return new THREE.Color(`rgb(${parts[0]}, ${parts[1]}, ${parts[2]})`);
  }
  return new THREE.Color('rgb(59, 130, 246)');
}

function useGeoJson(url: string) {
  const [data, setData] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    const clearId = requestAnimationFrame(() => setData(null));
    fetch(url)
      .then((r) => (r.ok ? r.json() : null))
      .then((json) => {
        if (cancelled) return;
        setData(json);
      })
      .catch(() => {
        if (cancelled) return;
        requestAnimationFrame(() => setData(null));
      });
    return () => {
      cancelled = true;
      cancelAnimationFrame(clearId);
    };
  }, [url]);

  return data;
}

type RegionLevel = 'countries' | 'admin1';
type BordersMode = 'off' | 'auto' | 'countries' | 'admin1';

type RegionFeature = {
  key: string;
  name: string;
  // Each polygon stores the outer ring only, coords are [lng, lat]
  polygons: Array<Array<[number, number]>>;
  bbox: { minLng: number; minLat: number; maxLng: number; maxLat: number };
};

type RegionIndex = {
  features: RegionFeature[];
  buckets: Map<string, number[]>;
  cellSize: number;
};

function normalizeLng(lng: number) {
  // Normalize into [-180, 180]
  let x = lng;
  while (x > 180) x -= 360;
  while (x < -180) x += 360;
  return x;
}

function computeRingBbox(ring: Array<[number, number]>) {
  let minLng = Infinity;
  let minLat = Infinity;
  let maxLng = -Infinity;
  let maxLat = -Infinity;
  for (const [lngRaw, latRaw] of ring) {
    const lng = normalizeLng(lngRaw);
    const lat = latRaw;
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) continue;
    minLng = Math.min(minLng, lng);
    maxLng = Math.max(maxLng, lng);
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
  }
  return { minLng, minLat, maxLng, maxLat };
}

function mergeBbox(a: RegionFeature['bbox'], b: RegionFeature['bbox']) {
  a.minLng = Math.min(a.minLng, b.minLng);
  a.minLat = Math.min(a.minLat, b.minLat);
  a.maxLng = Math.max(a.maxLng, b.maxLng);
  a.maxLat = Math.max(a.maxLat, b.maxLat);
}

function pointInRing(
  lngRaw: number,
  lat: number,
  ring: Array<[number, number]>
) {
  // Ray casting in 2D, ring coords are [lng, lat]
  const lng = normalizeLng(lngRaw);
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = normalizeLng(ring[i][0]);
    const yi = ring[i][1];
    const xj = normalizeLng(ring[j][0]);
    const yj = ring[j][1];

    const intersect =
      yi > lat !== yj > lat &&
      lng < ((xj - xi) * (lat - yi)) / (yj - yi + 1e-12) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function bucketKeyForPoint(lngRaw: number, lat: number, cellSize: number) {
  const lng = normalizeLng(lngRaw);
  const x = Math.floor((lng + 180) / cellSize);
  const y = Math.floor((lat + 90) / cellSize);
  return `${x}|${y}`;
}

function buildBuckets(features: RegionFeature[], cellSize: number) {
  const buckets = new Map<string, number[]>();

  const addIdx = (key: string, idx: number) => {
    const list = buckets.get(key);
    if (list) list.push(idx);
    else buckets.set(key, [idx]);
  };

  for (let i = 0; i < features.length; i++) {
    const b = features[i].bbox;
    if (!Number.isFinite(b.minLng) || !Number.isFinite(b.minLat)) continue;

    const minX = Math.floor((b.minLng + 180) / cellSize);
    const maxX = Math.floor((b.maxLng + 180) / cellSize);
    const minY = Math.floor((b.minLat + 90) / cellSize);
    const maxY = Math.floor((b.maxLat + 90) / cellSize);

    for (let x = minX; x <= maxX; x++) {
      for (let y = minY; y <= maxY; y++) addIdx(`${x}|${y}`, i);
    }
  }

  return buckets;
}

function buildRegionFeatures(
  geoJson: any,
  level: RegionLevel
): RegionFeature[] {
  const features = geoJson?.features;
  if (!Array.isArray(features)) return [];

  const out: RegionFeature[] = [];

  const getKey = (props: any) => {
    if (level === 'countries') {
      const iso =
        props?.ISO_A3 ||
        props?.ADM0_A3 ||
        props?.ADM0_A3_US ||
        props?.ISO3 ||
        props?.iso_a3;
      const name =
        props?.NAME || props?.ADMIN || props?.name || iso || 'Unknown';
      return { key: String(iso || name), name: String(name) };
    }
    const adm0 = props?.adm0_a3 || props?.ADM0_A3 || props?.ISO_A3 || '';
    const name = props?.name || props?.name_en || props?.NAME || '';
    const iso2 = props?.iso_3166_2 || props?.postal || '';
    const key = `${adm0}|${iso2 || name}`.trim();
    return {
      key: key || String(name || adm0 || 'admin1'),
      name: String(name || iso2 || key),
    };
  };

  const addPolygon = (props: any, poly: any) => {
    if (!Array.isArray(poly) || poly.length === 0) return;
    const outer = poly[0];
    if (!Array.isArray(outer) || outer.length < 3) return;
    const ring: Array<[number, number]> = [];
    for (const c of outer) {
      if (!Array.isArray(c) || c.length < 2) continue;
      const lng = Number(c[0]);
      const lat = Number(c[1]);
      if (!Number.isFinite(lng) || !Number.isFinite(lat)) continue;
      ring.push([lng, lat]);
    }
    if (ring.length < 3) return;

    const { key, name } = getKey(props);
    const bbox = computeRingBbox(ring);
    out.push({ key, name, polygons: [ring], bbox });
  };

  for (const f of features) {
    const g = f?.geometry;
    const type = g?.type;
    const coords = g?.coordinates;
    const props = f?.properties || {};
    if (!type || !coords) continue;
    if (type === 'Polygon') addPolygon(props, coords);
    if (type === 'MultiPolygon' && Array.isArray(coords)) {
      for (const poly of coords) addPolygon(props, poly);
    }
  }

  // Merge polygons that share the same key (countries can have multiple)
  const merged = new Map<string, RegionFeature>();
  for (const f of out) {
    const existing = merged.get(f.key);
    if (!existing) {
      merged.set(f.key, { ...f, polygons: [...f.polygons] });
      continue;
    }
    existing.polygons.push(...f.polygons);
    mergeBbox(existing.bbox, f.bbox);
  }

  return Array.from(merged.values());
}

function buildRegionIndex(
  geoJson: any,
  level: RegionLevel
): RegionIndex | null {
  const features = buildRegionFeatures(geoJson, level);
  if (features.length === 0) return null;
  const cellSize = level === 'countries' ? 10 : 6;
  const buckets = buildBuckets(features, cellSize);
  return { features, buckets, cellSize };
}

function computeRegionCounts(
  index: RegionIndex,
  points: Array<{ lat: number; lng: number }>,
  totalLocated: number
) {
  const countsSample = new Map<string, number>();
  let sampleTotal = 0;

  for (const p of points) {
    if (!Number.isFinite(p.lat) || !Number.isFinite(p.lng)) continue;
    sampleTotal += 1;
    const bucket = index.buckets.get(
      bucketKeyForPoint(p.lng, p.lat, index.cellSize)
    );
    if (!bucket) continue;
    let matchedKey: string | null = null;
    for (const idx of bucket) {
      const f = index.features[idx];
      const b = f.bbox;
      const lng = normalizeLng(p.lng);
      if (p.lat < b.minLat || p.lat > b.maxLat) continue;
      if (lng < b.minLng || lng > b.maxLng) continue;
      let hit = false;
      for (const ring of f.polygons) {
        if (pointInRing(lng, p.lat, ring)) {
          hit = true;
          break;
        }
      }
      if (hit) {
        matchedKey = f.key;
        break;
      }
    }
    if (!matchedKey) continue;
    countsSample.set(matchedKey, (countsSample.get(matchedKey) || 0) + 1);
  }

  const total = Math.max(0, totalLocated);
  const scale = sampleTotal > 0 ? total / sampleTotal : 1;
  const counts = new Map<string, number>();
  let maxCount = 0;

  for (const [k, v] of countsSample.entries()) {
    const scaled = Math.max(0, Math.round(v * scale));
    counts.set(k, scaled);
    maxCount = Math.max(maxCount, scaled);
  }

  return { counts, total, maxCount };
}

function drawRegionOverlayAlphaTexture(args: {
  index: RegionIndex;
  counts: Map<string, number>;
  total: number;
  maxCount: number;
  level: RegionLevel;
  width: number;
  height: number;
}) {
  const { index, counts, total, maxCount, level, width, height } = args;
  if (total <= 0 || maxCount <= 0 || counts.size === 0) return null;

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  ctx.clearRect(0, 0, width, height);
  ctx.imageSmoothingEnabled = true;

  const toXY = (lngRaw: number, lat: number) => {
    const lng = normalizeLng(lngRaw);
    const x = ((lng + 180) / 360) * width;
    const y = ((90 - lat) / 180) * height;
    return { x, y, lng };
  };

  // Draw only regions with photos; color is white, tinting is done via material.color.
  for (const f of index.features) {
    const count = counts.get(f.key) || 0;
    if (count <= 0) continue;

    const pct = count / total; // percentage of located photos
    const vol = Math.log1p(count) / Math.log1p(maxCount);
    const pctIntensity = clamp(pct / 0.12, 0, 1); // 12% of photos saturates
    const intensity = clamp(0.7 * pctIntensity + 0.3 * vol, 0, 1);

    const alpha = mix(0.06, 0.82, intensity);
    const strokeAlpha = mix(0.08, 0.92, intensity);

    ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
    ctx.strokeStyle = `rgba(255, 255, 255, ${strokeAlpha})`;
    ctx.lineWidth = level === 'countries' ? 1.15 : 0.9;

    for (const ring of f.polygons) {
      if (ring.length < 3) continue;
      ctx.beginPath();
      let prevLng: number | null = null;
      for (let i = 0; i < ring.length; i++) {
        const [lngRaw, lat] = ring[i];
        const { x, y, lng } = toXY(lngRaw, lat);
        if (prevLng !== null && Math.abs(lng - prevLng) > 180) {
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(x, y);
        } else if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
        prevLng = lng;
      }
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    }
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.anisotropy = 4;
  texture.needsUpdate = true;
  return texture;
}

function buildCountryBorderGeometry(
  geoJson: any,
  radius: number,
  quality: '110m' | '50m'
) {
  const positions: number[] = [];

  const pushSegment = (a: [number, number], b: [number, number]) => {
    const [lng1, lat1] = a;
    const [lng2, lat2] = b;
    if (Math.abs(lng2 - lng1) > 180) return; // avoid antimeridian wrap artifacts

    const v1 = latLngToVector3(lat1, lng1, radius);
    const v2 = latLngToVector3(lat2, lng2, radius);
    positions.push(v1.x, v1.y, v1.z, v2.x, v2.y, v2.z);
  };

  const chooseStep = (n: number) => {
    if (quality === '110m') return n > 600 ? 3 : n > 250 ? 2 : 1;
    return n > 1400 ? 4 : n > 700 ? 2 : 1;
  };

  const addRing = (ring: any[]) => {
    if (!Array.isArray(ring) || ring.length < 2) return;
    const step = chooseStep(ring.length);

    let prev: [number, number] | null = null;
    for (let i = 0; i < ring.length; i += step) {
      const c = ring[i];
      if (!Array.isArray(c) || c.length < 2) continue;
      const curr: [number, number] = [Number(c[0]), Number(c[1])];
      if (!Number.isFinite(curr[0]) || !Number.isFinite(curr[1])) continue;
      if (prev) pushSegment(prev, curr);
      prev = curr;
    }

    // Close the ring
    const first = ring[0];
    const last = ring[ring.length - 1];
    if (
      Array.isArray(first) &&
      Array.isArray(last) &&
      first.length >= 2 &&
      last.length >= 2
    ) {
      const a: [number, number] = [Number(last[0]), Number(last[1])];
      const b: [number, number] = [Number(first[0]), Number(first[1])];
      if (
        Number.isFinite(a[0]) &&
        Number.isFinite(a[1]) &&
        Number.isFinite(b[0]) &&
        Number.isFinite(b[1])
      ) {
        pushSegment(a, b);
      }
    }
  };

  const addPolygon = (coords: any[]) => {
    if (!Array.isArray(coords) || coords.length === 0) return;
    // Outer ring only for clarity/perf
    addRing(coords[0]);
  };

  const features = geoJson?.features;
  if (!Array.isArray(features)) return null;

  for (const f of features) {
    const g = f?.geometry;
    const type = g?.type;
    const coords = g?.coordinates;
    if (!type || !coords) continue;
    if (type === 'Polygon') addPolygon(coords);
    else if (type === 'MultiPolygon') {
      if (!Array.isArray(coords)) continue;
      for (const poly of coords) addPolygon(poly);
    }
  }

  if (positions.length === 0) return null;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    'position',
    new THREE.Float32BufferAttribute(positions, 3)
  );
  return geometry;
}

function buildLineBorderGeometry(
  geoJson: any,
  radius: number,
  opts?: { step?: number; maxSegments?: number }
) {
  const positions: number[] = [];
  const step = opts?.step ?? 2;
  const maxSegments = opts?.maxSegments ?? 200_000;

  const pushSegment = (a: [number, number], b: [number, number]) => {
    const [lng1, lat1] = a;
    const [lng2, lat2] = b;
    if (Math.abs(lng2 - lng1) > 180) return;
    const v1 = latLngToVector3(lat1, lng1, radius);
    const v2 = latLngToVector3(lat2, lng2, radius);
    positions.push(v1.x, v1.y, v1.z, v2.x, v2.y, v2.z);
  };

  const addLineString = (coords: any[]) => {
    if (!Array.isArray(coords) || coords.length < 2) return;
    let prev: [number, number] | null = null;
    for (let i = 0; i < coords.length; i += step) {
      const c = coords[i];
      if (!Array.isArray(c) || c.length < 2) continue;
      const curr: [number, number] = [Number(c[0]), Number(c[1])];
      if (!Number.isFinite(curr[0]) || !Number.isFinite(curr[1])) continue;
      if (prev) pushSegment(prev, curr);
      prev = curr;
      if (positions.length / 6 > maxSegments) return;
    }
  };

  const features = geoJson?.features;
  if (!Array.isArray(features)) return null;

  for (const f of features) {
    const g = f?.geometry;
    const type = g?.type;
    const coords = g?.coordinates;
    if (!type || !coords) continue;
    if (type === 'LineString') addLineString(coords);
    else if (type === 'MultiLineString') {
      if (!Array.isArray(coords)) continue;
      for (const line of coords) {
        addLineString(line);
        if (positions.length / 6 > maxSegments) break;
      }
    }
    if (positions.length / 6 > maxSegments) break;
  }

  if (positions.length === 0) return null;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    'position',
    new THREE.Float32BufferAttribute(positions, 3)
  );
  return geometry;
}

// Convert lat/lng to 3D position on sphere
function latLngToVector3(
  lat: number,
  lng: number,
  radius: number
): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  const x = -(radius * Math.sin(phi) * Math.cos(theta));
  const y = radius * Math.cos(phi);
  const z = radius * Math.sin(phi) * Math.sin(theta);
  return new THREE.Vector3(x, y, z);
}

type Cluster = {
  lat: number;
  lng: number;
  position: THREE.Vector3;
  photos: Photo[];
  count: number;
};

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function mix(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function colorForCount(count: number, accent: THREE.Color) {
  const t = clamp(Math.log1p(count) / Math.log(40), 0, 1);
  const highlight = new THREE.Color('#a855f7'); // purple
  return accent.clone().lerp(highlight, t * 0.55);
}

function clusterPhotos(
  photos: Photo[],
  cellDeg: number
): {
  clusters: Cluster[];
  representativePhoto: Photo | null;
  missingGpsCount: number;
  locatedCount: number;
} {
  const buckets = new Map<
    string,
    { lat: number; lng: number; photos: Photo[] }
  >();

  const add = (photo: Photo, lat: number, lng: number) => {
    const qLat = Math.round(lat / cellDeg) * cellDeg;
    const qLng = Math.round(lng / cellDeg) * cellDeg;
    const key = `${qLat.toFixed(3)}|${qLng.toFixed(3)}`;
    const existing = buckets.get(key);
    if (existing) {
      existing.photos.push(photo);
    } else {
      buckets.set(key, { lat: qLat, lng: qLng, photos: [photo] });
    }
  };

  let missingGpsCount = 0;

  photos.forEach((photo) => {
    const lat = photo.metadata?.gps?.latitude;
    const lng = photo.metadata?.gps?.longitude;
    if (typeof lat !== 'number' || typeof lng !== 'number') {
      missingGpsCount += 1;
      return;
    }
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      missingGpsCount += 1;
      return;
    }
    add(photo, lat, lng);
  });

  const clusters: Cluster[] = [];
  let representativePhoto: Photo | null = null;

  for (const bucket of buckets.values()) {
    const count = bucket.photos.length;
    const position = latLngToVector3(bucket.lat, bucket.lng, 7);
    clusters.push({
      lat: bucket.lat,
      lng: bucket.lng,
      position,
      photos: bucket.photos,
      count,
    });
    if (!representativePhoto) representativePhoto = bucket.photos[0];
  }

  clusters.sort((a, b) => b.count - a.count);
  return {
    clusters,
    representativePhoto,
    missingGpsCount,
    locatedCount: photos.length - missingGpsCount,
  };
}

function getClusterCellDeg(cameraDistance: number) {
  if (cameraDistance <= 12) return 0.5;
  if (cameraDistance <= 15) return 1;
  if (cameraDistance <= 18) return 2;
  if (cameraDistance <= 22) return 3.5;
  if (cameraDistance <= 26) return 5;
  return 7;
}

function RegionGlass({
  cluster,
  accent,
  hovered,
}: {
  cluster: Cluster;
  accent: THREE.Color;
  hovered: boolean;
}) {
  const count = cluster.count;
  const t = clamp(Math.log1p(count) / Math.log(40), 0, 1);
  const density = Math.pow(t, 1.35);

  const normal = cluster.position.clone().normalize();
  const adjustedPosition = normal.clone().multiplyScalar(7.005);
  const quaternion = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    normal
  );

  const radius = 0.16 + Math.log1p(count) * 0.05;
  const opacity = hovered ? 0.9 : mix(0.01, 0.72, density);
  const transmission = hovered ? 0.25 : mix(0.88, 0.35, density);
  const color = colorForCount(count, accent);

  return (
    <mesh position={adjustedPosition} quaternion={quaternion} renderOrder={1}>
      <circleGeometry args={[radius, 22]} />
      <meshPhysicalMaterial
        color={color}
        roughness={mix(0.15, 0.45, t)}
        metalness={0.05}
        clearcoat={1}
        clearcoatRoughness={0.2}
        transmission={transmission}
        thickness={0.6}
        ior={1.35}
        transparent
        opacity={opacity}
        depthWrite={false}
      />
    </mesh>
  );
}

function CountryBorders({ accent }: { accent: THREE.Color }) {
  const camera = useThree((s) => s.camera);
  const materialRef = useRef<THREE.LineBasicMaterial | null>(null);
  const [detail, setDetail] = useState<'110m' | '50m'>('110m');
  const detailRef = useRef<'110m' | '50m'>('110m');
  const frameCountRef = useRef(0);

  useFrame(() => {
    frameCountRef.current++;
    // Only update every 10 frames to reduce performance impact
    if (frameCountRef.current % 10 !== 0) return;

    const d = camera.position.length();
    const prev = detailRef.current;
    const next =
      prev === '110m' ? (d < 15 ? '50m' : '110m') : d > 16.5 ? '110m' : '50m';
    if (next !== prev) {
      detailRef.current = next;
      setDetail(next);
    }

    if (materialRef.current) {
      const t = clamp((22 - d) / 10, 0, 1);
      materialRef.current.opacity = 0.05 + t * 0.32;
    }
  });

  useEffect(() => {
    if (materialRef.current) materialRef.current.color.copy(accent);
  }, [accent]);

  const url =
    detail === '50m'
      ? '/ne_50m_admin_0_countries.geojson'
      : '/ne_110m_admin_0_countries.geojson';
  const geoJson = useGeoJson(url);

  const geometry = useMemo(() => {
    if (!geoJson) return null;
    return buildCountryBorderGeometry(geoJson, 7.015, detail);
  }, [geoJson, detail]);

  useEffect(() => {
    return () => {
      geometry?.dispose();
    };
  }, [geometry]);

  if (!geometry) return null;

  return (
    <lineSegments geometry={geometry} renderOrder={2}>
      <lineBasicMaterial
        ref={materialRef}
        color={accent}
        transparent
        opacity={0.18}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </lineSegments>
  );
}

function Admin1Borders({ accent }: { accent: THREE.Color }) {
  const camera = useThree((s) => s.camera);
  const materialRef = useRef<THREE.LineBasicMaterial | null>(null);
  const [enabled, setEnabled] = useState(false);
  const frameCountRef = useRef(0);

  useFrame(() => {
    frameCountRef.current++;
    // Only update every 15 frames to reduce performance impact
    if (frameCountRef.current % 15 !== 0) return;

    const d = camera.position.length();
    const on = d < 14.5;
    if (on !== enabled) setEnabled(on);
    if (materialRef.current) {
      const t = clamp((14.5 - d) / 4.5, 0, 1);
      materialRef.current.opacity = 0.02 + t * 0.2;
    }
  });

  useEffect(() => {
    if (materialRef.current) materialRef.current.color.copy(accent);
  }, [accent]);

  const geoJson = useGeoJson('/ne_50m_admin_1_states_provinces_lines.geojson');

  const geometry = useMemo(() => {
    if (!geoJson) return null;
    return buildLineBorderGeometry(geoJson, 7.016, {
      step: 2,
      maxSegments: 180_000,
    });
  }, [geoJson]);

  useEffect(() => {
    return () => {
      geometry?.dispose();
    };
  }, [geometry]);

  if (!enabled || !geometry) return null;

  return (
    <lineSegments geometry={geometry} renderOrder={3}>
      <lineBasicMaterial
        ref={materialRef}
        color={accent}
        transparent
        opacity={0.12}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </lineSegments>
  );
}

function RegionFillOverlay({
  level,
  accent,
  points,
  countryDetail,
  totalLocated,
}: {
  level: RegionLevel;
  accent: THREE.Color;
  points: Array<{ lat: number; lng: number }>;
  countryDetail?: '110m' | '50m';
  totalLocated: number;
}) {
  const url =
    level === 'admin1'
      ? '/ne_50m_admin_1_states_provinces.geojson'
      : countryDetail === '50m'
      ? '/ne_50m_admin_0_countries.geojson'
      : '/ne_110m_admin_0_countries.geojson';
  const geoJson = useGeoJson(url);

  const index = useMemo(() => {
    if (!geoJson) return null;
    return buildRegionIndex(geoJson, level);
  }, [geoJson, level]);

  const { counts, total, maxCount } = useMemo(() => {
    if (!index)
      return { counts: new Map<string, number>(), total: 0, maxCount: 0 };
    return computeRegionCounts(index, points, totalLocated);
  }, [index, points, totalLocated]);

  const texture = useMemo(() => {
    if (!index) return null;
    if (points.length === 0) return null;
    // Texture resolution: 2k is crisp enough without being too heavy.
    const width = 2048;
    const height = 1024;
    return drawRegionOverlayAlphaTexture({
      index,
      counts,
      total,
      maxCount,
      level,
      width,
      height,
    });
  }, [counts, index, level, maxCount, points.length, total]);

  useEffect(() => {
    return () => {
      texture?.dispose();
    };
  }, [texture]);

  if (!texture) return null;

  return (
    <mesh scale={1.007} renderOrder={1}>
      <sphereGeometry args={[7, 64, 64]} />
      <meshPhysicalMaterial
        map={texture}
        color={accent}
        transparent
        opacity={1}
        depthWrite={false}
        roughness={0.32}
        metalness={0.06}
        clearcoat={1}
        clearcoatRoughness={0.22}
        transmission={0.75}
        thickness={0.9}
        ior={1.35}
      />
    </mesh>
  );
}

// Individual photo marker on globe
function PhotoMarker({
  cluster,
  position,
  onSelect,
  onHoverChange,
  accent,
}: {
  cluster: Cluster;
  position: THREE.Vector3;
  onSelect: (p: Photo) => void;
  // index was previously passed but is unused - remove it to avoid lint
  onHoverChange?: (p: Photo | null) => void;
  accent: THREE.Color;
}) {
  const [hovered, setHovered] = useState(false);

  // Floating animation handled by parent rotation mostly,
  // but we can add local scale pulse
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      // Constantly face camera
      meshRef.current.lookAt(state.camera.position);
    }
  });

  const count = cluster.count;
  const primary = cluster.photos[0];

  const height = 0.2 + Math.pow(Math.log1p(count), 1.22) * 0.28;
  const radius = 0.058 + Math.pow(Math.log1p(count), 1.08) * 0.035;
  const t = clamp(Math.log1p(count) / Math.log(40), 0, 1);
  const barColor = colorForCount(count, accent);

  const normal = position.clone().normalize();
  const adjustedPosition = normal.clone().multiplyScalar(7.02);
  const quaternion = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    normal
  );

  return (
    <group position={adjustedPosition}>
      <mesh
        ref={meshRef}
        onPointerOver={(e) => {
          e.stopPropagation();
          document.body.style.cursor = 'pointer';
          setHovered(true);
          onHoverChange?.(primary);
        }}
        onPointerOut={(e) => {
          e.stopPropagation();
          document.body.style.cursor = 'auto';
          setHovered(false);
          onHoverChange?.(null);
        }}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(primary);
        }}
        quaternion={quaternion}
      >
        {/* Larger invisible hit target */}
        <cylinderGeometry
          args={[radius * 2.2, radius * 2.2, height + 0.6, 10]}
        />
        <meshBasicMaterial transparent opacity={0.0} />

        {/* Glassy bar that scales with density */}
        <mesh position={[0, height / 2, 0]}>
          <cylinderGeometry args={[radius, radius, height, 10]} />
          <meshPhysicalMaterial
            color={barColor}
            roughness={mix(0.55, 0.25, t)}
            metalness={0.1}
            clearcoat={1}
            clearcoatRoughness={0.18}
            transmission={mix(0.2, 0.55, 1 - t)}
            ior={1.25}
            transparent
            opacity={hovered ? 0.98 : mix(0.25, 0.92, t)}
            emissive={hovered ? accent : new THREE.Color('#000000')}
            emissiveIntensity={hovered ? 0.22 : 0.08}
          />
        </mesh>

        {/* Cap */}
        <mesh position={[0, height + 0.06, 0]}>
          <sphereGeometry args={[radius * 0.92, 12, 12]} />
          <meshPhysicalMaterial
            color={barColor}
            roughness={0.3}
            metalness={0.15}
            clearcoat={1}
            clearcoatRoughness={0.12}
            transmission={0.35}
            ior={1.25}
            transparent
            opacity={hovered ? 1 : mix(0.35, 0.95, t)}
            emissive={
              hovered
                ? accent.clone().lerp(new THREE.Color('#ffffff'), 0.35)
                : new THREE.Color('#000000')
            }
            emissiveIntensity={hovered ? 0.25 : 0.08}
          />
        </mesh>
      </mesh>

      {/* Photo thumbnail on hover */}
      {hovered && (
        <Billboard follow={true} lockX={false} lockY={false} lockZ={false}>
          <Html distanceFactor={10} center zIndexRange={[100, 0]}>
            <div className='glass-surface glass-surface--strong rounded-xl p-2 shadow-2xl transform -translate-y-8 cursor-pointer pointer-events-none w-max'>
              <SecureLazyImage
                path={primary.path}
                size={150}
                alt={primary.filename}
                className='w-32 h-24 rounded-lg'
                showBadge={false}
              />
              <p className='text-white text-xs mt-1 text-center truncate max-w-32 font-medium'>
                {primary.filename}
              </p>
              {count > 1 && (
                <p className='text-white/70 text-[11px] mt-0.5 text-center'>
                  +{count - 1} more
                </p>
              )}
            </div>
          </Html>
        </Billboard>
      )}
    </group>
  );
}

// The Rotating Earth Group containing Globe + Markers
function RotatingEarth({
  photos,
  onPhotoSelect,
  isRotating,
  onPhotoHover,
  borderMode,
}: {
  photos: Photo[];
  onPhotoSelect: (p: Photo) => void;
  isRotating: boolean;
  onPhotoHover?: (p: Photo | null) => void;
  borderMode: BordersMode;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const colorMap = useLoader(THREE.TextureLoader, '/earth_texture.jpg');
  const camera = useThree((state) => state.camera);
  const [cellDeg, setCellDeg] = useState(6);
  const cellDegRef = useRef(6);
  const [accent, setAccent] = useState(() => parseCssAccentRgb());
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const [countryDetail, setCountryDetail] = useState<'110m' | '50m'>('110m');
  const countryDetailRef = useRef<'110m' | '50m'>('110m');
  const frameCountRef = useRef(0);
  const [effectiveRegionLevel, setEffectiveRegionLevel] =
    useState<RegionLevel>('countries');

  const earthMaterial = useMemo(() => {
    const mat = new THREE.MeshStandardMaterial({
      map: colorMap,
      roughness: 0.92,
      metalness: 0,
      transparent: true,
      opacity: 0.64,
      emissive: new THREE.Color('#000000'),
      emissiveIntensity: 0.2,
    });

    // De-saturate the texture so it matches the app's glass language.
    mat.onBeforeCompile = (shader) => {
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <map_fragment>',
        `
#ifdef USE_MAP
  vec4 sampledDiffuseColor = texture2D( map, vMapUv );
  float luma = dot(sampledDiffuseColor.rgb, vec3(0.299, 0.587, 0.114));
  vec3 desat = vec3(luma);
  sampledDiffuseColor.rgb = mix(desat, sampledDiffuseColor.rgb, 0.12);
  diffuseColor *= sampledDiffuseColor;
#endif
        `
      );
    };
    mat.needsUpdate = true;
    return mat;
  }, [colorMap]);

  useEffect(() => {
    return () => {
      earthMaterial.dispose();
    };
  }, [earthMaterial]);

  useEffect(() => {
    const tint = accent.clone().lerp(new THREE.Color('#ffffff'), 0.72);
    earthMaterial.color.copy(tint);
    earthMaterial.emissive.copy(accent.clone().multiplyScalar(0.12));
  }, [accent, earthMaterial]);

  useFrame(() => {
    const frame = (frameCountRef.current += 1);

    // Gentle auto-rotation
    if (groupRef.current && isRotating) {
      groupRef.current.rotation.y += 0.0005;
    }

    // Only update every 20 frames for cluster cell calculations
    if (frame % 20 === 0) {
      const distance = camera.position.length();
      const nextCell = getClusterCellDeg(distance);
      if (nextCell !== cellDegRef.current) {
        cellDegRef.current = nextCell;
        setCellDeg(nextCell);
      }
    }

    // Only update every 25 frames for detail level calculations
    if (frame % 25 !== 0) return;

    const d = camera.position.length();
    const nextDetail =
      countryDetailRef.current === '110m'
        ? d < 15
          ? '50m'
          : '110m'
        : d > 16.5
        ? '110m'
        : '50m';
    if (nextDetail !== countryDetailRef.current) {
      countryDetailRef.current = nextDetail;
      setCountryDetail(nextDetail);
    }

    const nextLevel =
      borderMode === 'admin1'
        ? 'admin1'
        : borderMode === 'countries'
        ? 'countries'
        : borderMode === 'auto'
        ? d < 15.2
          ? 'admin1'
          : 'countries'
        : 'countries';
    if (borderMode === 'off') return;
    if (nextLevel !== effectiveRegionLevel) setEffectiveRegionLevel(nextLevel);
  });

  useEffect(() => {
    const sync = () => setAccent(parseCssAccentRgb());
    sync();
    window.addEventListener('lm:prefChange', sync as EventListener);
    const interval = window.setInterval(sync, 500);
    return () => {
      window.removeEventListener('lm:prefChange', sync as EventListener);
      window.clearInterval(interval);
    };
  }, []);

  const clustered = useMemo(
    () => clusterPhotos(photos.slice(0, 800), cellDeg),
    [photos, cellDeg]
  );
  const clusters = clustered.clusters;
  const locationCounts = useMemo(() => {
    let missing = 0;
    let located = 0;
    for (const p of photos) {
      const lat = p.metadata?.gps?.latitude;
      const lng = p.metadata?.gps?.longitude;
      if (typeof lat !== 'number' || typeof lng !== 'number') {
        missing += 1;
        continue;
      }
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        missing += 1;
        continue;
      }
      located += 1;
    }
    return { missingGpsCount: missing, locatedCount: located };
  }, [photos]);
  const missingGpsCount = locationCounts.missingGpsCount;
  const locatedCount = locationCounts.locatedCount;

  const pointsForRegions = useMemo(() => {
    const pts: Array<{ lat: number; lng: number }> = [];
    // Use more samples for region fill, but cap for perf.
    const max = 6000;
    const stride = Math.max(1, Math.ceil(photos.length / max));
    for (let i = 0; i < photos.length && pts.length < max; i += stride) {
      const lat = photos[i]?.metadata?.gps?.latitude;
      const lng = photos[i]?.metadata?.gps?.longitude;
      if (typeof lat !== 'number' || typeof lng !== 'number') continue;
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
      pts.push({ lat, lng });
    }
    return pts;
  }, [photos]);

  return (
    <group ref={groupRef}>
      {/* Earth Core (texture) */}
      <mesh>
        <sphereGeometry args={[7, 64, 64]} />
        <primitive object={earthMaterial} attach='material' />
      </mesh>

      {/* Glass Shell (brings it into the app glass language) */}
      <mesh scale={1.003}>
        <sphereGeometry args={[7, 64, 64]} />
        <meshPhysicalMaterial
          color={accent}
          roughness={0.25}
          metalness={0.12}
          clearcoat={1}
          clearcoatRoughness={0.18}
          transmission={0.72}
          thickness={1.1}
          ior={1.35}
          transparent
          opacity={0.18}
        />
      </mesh>

      {/* Atmosphere glow */}
      <mesh scale={1.02}>
        <sphereGeometry args={[7, 32, 32]} />
        <meshBasicMaterial
          color={accent}
          transparent
          opacity={0.12}
          side={THREE.BackSide}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Country borders (110m when zoomed out, 50m when zoomed in) */}
      {borderMode !== 'off' && <CountryBorders accent={accent} />}
      {(borderMode === 'admin1' || borderMode === 'auto') && (
        <Admin1Borders accent={accent} />
      )}

      {/* Region glass fill: countries zoomed out, admin-1 zoomed in (intensity from % of photos) */}
      {borderMode !== 'off' && pointsForRegions.length > 0 && (
        <RegionFillOverlay
          level={borderMode === 'auto' ? effectiveRegionLevel : borderMode}
          accent={accent}
          points={pointsForRegions}
          countryDetail={countryDetail}
          totalLocated={locatedCount}
        />
      )}

      {/* Region glass overlays (density makes glass more visible) */}
      {clusters.slice(0, 220).map((item) => {
        const key = `${item.lat}-${item.lng}`;
        return (
          <RegionGlass
            key={`glass-${key}`}
            cluster={item}
            accent={accent}
            hovered={hoveredKey === key}
          />
        );
      })}

      {/* Markers nested inside the rotating group */}
      {clusters.slice(0, 220).map((item) => (
        <PhotoMarker
          key={`${item.lat}-${item.lng}`}
          cluster={item}
          position={item.position}
          onSelect={onPhotoSelect}
          onHoverChange={(p) => {
            onPhotoHover?.(p);
            setHoveredKey(p ? `${item.lat}-${item.lng}` : null);
          }}
          accent={accent}
        />
      ))}

      {/* Small in-world label for missing GPS */}
      {missingGpsCount > 0 && (
        <Html position={[0, -8.6, 0]} center>
          <div className='glass-surface rounded-full px-3 py-1 text-[11px] text-white/80'>
            {locatedCount.toLocaleString()} located •{' '}
            {missingGpsCount.toLocaleString()} without GPS
          </div>
        </Html>
      )}
    </group>
  );
}

// Loading fallback
function LoadingFallback() {
  return (
    <Html center>
      <div className='text-white text-center'>
        <div className='w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4' />
        <p className='text-sm opacity-70'>Loading Earth...</p>
      </div>
    </Html>
  );
}

export function PhotoGlobe({
  photos,
  onPhotoSelect,
  onClose,
  variant = 'embedded',
}: PhotoGlobeProps) {
  const [isRotating, setIsRotating] = useState(true);
  const [showHelp, setShowHelp] = useState(false);
  const [borderMode, setBorderMode] = useState<BordersMode>('auto');
  const [hoveredPhoto, setHoveredPhoto] = useState<Photo | null>(null);
  const { setOverrideAccentUrl, clearOverrideAccent } =
    useAmbientThemeContext();

  const locationStats = useMemo(() => {
    let located = 0;
    for (const p of photos) {
      const lat = p.metadata?.gps?.latitude;
      const lng = p.metadata?.gps?.longitude;
      if (typeof lat === 'number' && typeof lng === 'number') located += 1;
    }
    return { located, missing: photos.length - located };
  }, [photos]);

  useEffect(() => {
    let mounted = true;
    async function setAccent() {
      if (!hoveredPhoto) return;
      try {
        const url = await api.getSignedImageUrl(hoveredPhoto.path, 96);
        if (!mounted) return;
        setOverrideAccentUrl(
          'globeHover',
          url || api.getImageUrl(hoveredPhoto.path, 96)
        );
      } catch (e) {
        if (!mounted) return;
        setOverrideAccentUrl(
          'globeHover',
          api.getImageUrl(hoveredPhoto.path, 96)
        );
      }
    }

    if (hoveredPhoto) setAccent();
    else clearOverrideAccent('globeHover');
    return () => {
      mounted = false;
      clearOverrideAccent('globeHover');
    };
  }, [hoveredPhoto, setOverrideAccentUrl, clearOverrideAccent]);

  // Space key to toggle rotation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && e.target === document.body) {
        e.preventDefault();
        setIsRotating((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const containerClassName =
    variant === 'fullscreen'
      ? 'fixed inset-0 z-40 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-900 via-[#0a0a0a] to-black'
      : 'relative w-full h-full';

  return (
    <div className={containerClassName}>
      {/* Controls */}
      <div className='absolute top-3 right-3 z-50 flex items-center gap-2'>
        <button
          onClick={() => setIsRotating(!isRotating)}
          className='btn-glass btn-glass--muted w-10 h-10 p-0 justify-center text-white/80'
          title={isRotating ? 'Pause rotation' : 'Resume rotation'}
          aria-label={isRotating ? 'Pause rotation' : 'Resume rotation'}
        >
          {isRotating ? <Pause size={18} /> : <Play size={18} />}
        </button>

        <button
          onClick={() =>
            setBorderMode((m) =>
              m === 'off'
                ? 'auto'
                : m === 'auto'
                ? 'countries'
                : m === 'countries'
                ? 'admin1'
                : 'off'
            )
          }
          className={`btn-glass ${
            borderMode === 'off' ? 'btn-glass--muted' : 'btn-glass--primary'
          } w-10 h-10 p-0 justify-center`}
          title={
            borderMode === 'off'
              ? 'Show borders'
              : borderMode === 'auto'
              ? 'Borders: Auto (countries → admin-1 on zoom)'
              : borderMode === 'countries'
              ? 'Borders: Countries (click for admin-1)'
              : 'Borders: Admin-1 (click to hide)'
          }
          aria-label='Borders'
        >
          <MapIcon size={18} />
        </button>

        <button
          onClick={() => setShowHelp((v) => !v)}
          className='btn-glass btn-glass--muted w-10 h-10 p-0 justify-center text-white/80'
          title='Help'
          aria-label='Help'
        >
          <HelpCircle size={18} />
        </button>

        {variant === 'fullscreen' && onClose && (
          <button
            onClick={onClose}
            className='btn-glass btn-glass--danger text-xs px-3 py-2'
            title='Exit globe'
          >
            Exit
          </button>
        )}
      </div>

      {showHelp && (
        <div className='absolute top-3 left-3 z-50 glass-surface glass-surface--strong rounded-2xl p-3 text-xs text-white/80 max-w-[260px]'>
          <div className='font-semibold text-white/90 mb-1'>Globe</div>
          <div className='text-white/70'>
            Drag to orbit • Scroll to zoom (clusters split as you zoom in) •
            Click a marker to open details.
            <div className='mt-2 text-white/60'>
              Borders:{' '}
              {borderMode === 'off'
                ? 'Off'
                : borderMode === 'auto'
                ? 'Auto'
                : borderMode === 'countries'
                ? 'Countries'
                : 'Admin-1'}
            </div>
            {locationStats.missing > 0 && (
              <div className='mt-2 text-white/60'>
                Location metadata: {locationStats.located.toLocaleString()} with
                GPS • {locationStats.missing.toLocaleString()} without GPS
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3D Canvas */}
      <Canvas
        camera={{ position: [0, 0, 18], fov: 45 }}
        dpr={[1, 2]}
        className='w-full h-full'
      >
        <Suspense fallback={<LoadingFallback />}>
          <ambientLight intensity={0.18} />
          <directionalLight
            position={[15, 10, 5]}
            intensity={1.2}
            color='#ffd4a3'
          />
          <pointLight
            position={[-10, -10, -5]}
            intensity={0.45}
            color='#60a5fa'
          />
          <Stars
            radius={100}
            depth={50}
            count={2000}
            factor={4}
            saturation={0}
            fade
            speed={0.35}
          />
          <RotatingEarth
            photos={photos}
            onPhotoSelect={onPhotoSelect}
            isRotating={isRotating}
            onPhotoHover={setHoveredPhoto}
            borderMode={borderMode}
          />
          <OrbitControls
            makeDefault
            enableDamping
            dampingFactor={0.05}
            minDistance={10}
            maxDistance={30}
            enablePan={false}
          />
        </Suspense>
      </Canvas>
    </div>
  );
}

export default PhotoGlobe;
