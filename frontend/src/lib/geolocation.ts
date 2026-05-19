export type ResolvedLocation = {
  lat: number;
  lon: number;
  source: "gps" | "ip" | "stored" | "default";
};

const STORAGE_KEY = "clima_kids_last_location";

export function loadStoredLocation(): ResolvedLocation | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as ResolvedLocation;
    if (typeof data.lat === "number" && typeof data.lon === "number") return data;
  } catch {
    /* ignore */
  }
  return null;
}

export function storeLocation(loc: ResolvedLocation) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(loc));
}

function browserGeolocation(timeoutMs = 12_000): Promise<ResolvedLocation> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Géolocalisation non supportée"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const loc: ResolvedLocation = {
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          source: "gps",
        };
        storeLocation(loc);
        resolve(loc);
      },
      (err) => reject(err),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 60_000 },
    );
  });
}

async function ipFallback(): Promise<ResolvedLocation> {
  const base = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";
  const resp = await fetch(`${base}/public/geo/ip-location`);
  if (!resp.ok) throw new Error("IP geolocation failed");
  const data = await resp.json();
  const loc: ResolvedLocation = {
    lat: Number(data.lat),
    lon: Number(data.lon),
    source: data.source === "ip" ? "ip" : "default",
  };
  storeLocation(loc);
  return loc;
}

/** GPS → last known → IP/default (server-side). */
export async function resolveUserLocation(): Promise<ResolvedLocation> {
  try {
    return await browserGeolocation();
  } catch {
    const stored = loadStoredLocation();
    if (stored) return { ...stored, source: "stored" };
    return ipFallback();
  }
}
