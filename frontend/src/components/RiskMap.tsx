"use client";

import type { FeatureCollection } from "geojson";
import { useMemo } from "react";
import { GeoJSON as RLGeoJSON, MapContainer, TileLayer } from "react-leaflet";

type Props = {
  zones: FeatureCollection;
};

export function RiskMap({ zones }: Props) {
  const style = useMemo(
    () => ({
      color: "#1B4332",
      weight: 2,
      fillOpacity: 0.35,
    }),
    [],
  );

  return (
    <MapContainer
      center={[-10.7147, 25.4667]}
      zoom={12}
      className="h-[420px] w-full rounded-xl"
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <RLGeoJSON
        data={zones}
        style={(feat) => {
          const sev = (feat?.properties as { severity?: string } | undefined)?.severity;
          const fill =
            sev === "critical"
              ? "#D90429"
              : sev === "high"
                ? "#F77F00"
                : sev === "moderate"
                  ? "#FBBF24"
                  : "#2D6A4F";
          return { ...style, fillColor: fill };
        }}
      />
    </MapContainer>
  );
}
