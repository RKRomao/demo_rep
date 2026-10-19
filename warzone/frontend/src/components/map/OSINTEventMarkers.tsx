import React from 'react';
import { Marker, Popup, Circle } from 'react-leaflet';
import L from 'leaflet';
import { parseGeoJSONCoordinates } from './LeafletSetup';

interface OSINTEventFeature {
  id: number | string;
  type: string;
  geometry: {
    type: 'Point';
    coordinates: [number, number]; // [Longitude, Latitude] da MariaDB/GeoJSON
  };
  properties: {
    id: number;
    title: string;
    description?: string;
    category: string;
    precision_class?: 'HIGH_PRECISION' | 'LOW_PRECISION' | 'UNKNOWN';
    location_name?: string;
    source_name?: string;
    event_timestamp?: string;
  };
}

interface OSINTEventMarkersProps {
  events: OSINTEventFeature[];
}

// Algoritmo de Jittering Geográfico (Dispersão orbital para coordenadas idênticas)
function applyJittering(lat: number, lng: number, index: number, totalCount: number): [number, number] {
  if (!totalCount || totalCount <= 1) return [lat, lng];
  const radius = 0.008; // ~800 metros
  const angle = (index / totalCount) * 2 * Math.PI;
  return [lat + radius * Math.sin(angle), lng + radius * Math.cos(angle)];
}

export const OSINTEventMarkers: React.FC<OSINTEventMarkersProps> = ({ events }) => {
  // Mapeamento de contagem de coordenadas para aplicar Jittering
  const coordCounts: Record<string, number> = {};
  events.forEach((evt) => {
    if (evt.geometry?.coordinates) {
      const [lng, lat] = evt.geometry.coordinates;
      const key = `${lat.toFixed(3)}_${lng.toFixed(3)}`;
      coordCounts[key] = (coordCounts[key] || 0) + 1;
    }
  });

  const coordIndexes: Record<string, number> = {};

  return (
    <>
      {events.map((evt) => {
        if (!evt.geometry || !evt.geometry.coordinates) return null;

        // 1. INVERSÃO SEGURA DE COORDENADAS GEOJSON: [Lng, Lat] -> [Lat, Lng]
        const [origLat, origLng] = parseGeoJSONCoordinates(evt.geometry.coordinates);
        const key = `${origLat.toFixed(3)}_${origLng.toFixed(3)}`;

        coordIndexes[key] = (coordIndexes[key] || 0) + 1;
        const index = coordIndexes[key];
        const total = coordCounts[key];

        // 2. DISPERSÃO GEOGRÁFICA (JITTERING)
        const [lat, lng] = applyJittering(origLat, origLng, index, total);

        const isLowPrecision = evt.properties.precision_class === 'LOW_PRECISION';

        if (isLowPrecision) {
          // RENDERIZAÇÃO DE LOW_PRECISION (RAIO DIFUSO DE IMPACTO URBANO DE 4 KM)
          return (
            <Circle
              key={evt.properties.id || evt.id}
              center={[origLat, origLng]}
              radius={4000} // 4km
              pathOptions={{
                color: '#F59E0B',
                fillColor: '#F59E0B',
                fillOpacity: 0.22,
                weight: 1,
                dashArray: '4, 4',
              }}
            >
              <Popup className="tactical-popup">
                <div className="event-popup-content">
                  <span className="badge" style={{ background: '#B45309', color: '#FFF', padding: '2px 6px', borderRadius: '4px', fontSize: '10px' }}>
                    ÁREA APROXIMADA (LOW_PRECISION)
                  </span>
                  <h4 style={{ margin: '6px 0 2px 0' }}>{evt.properties.title}</h4>
                  <p>{evt.properties.description || 'Evento OSINT reportado na área urbana.'}</p>
                </div>
              </Popup>
            </Circle>
          );
        }

        // RENDERIZAÇÃO DE HIGH_PRECISION (MARCADOR PONTUAL EXATO)
        const customIcon = L.divIcon({
          html: `<div class="marker-pulse marker-cyan"><i class="fa-solid fa-crosshairs"></i></div>`,
          className: 'custom-tactical-marker',
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        });

        return (
          <Marker key={evt.properties.id || evt.id} position={[lat, lng]} icon={customIcon}>
            <Popup className="tactical-popup">
              <div className="event-popup-content">
                <span className="badge" style={{ background: '#047857', color: '#FFF', padding: '2px 6px', borderRadius: '4px', fontSize: '10px' }}>
                  COORDENADA EXATA (HIGH_PRECISION)
                </span>
                <h4 style={{ margin: '6px 0 2px 0' }}>{evt.properties.title}</h4>
                <p><strong>Setor:</strong> {evt.properties.location_name || 'Desconhecido'}</p>
                <p>{evt.properties.description}</p>
                <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '6px' }}>
                  Fonte: {evt.properties.source_name || 'OSINT'}
                </div>
              </div>
            </Popup>
          </Marker>
        );
      })}
    </>
  );
};
