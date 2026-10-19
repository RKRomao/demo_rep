import React from 'react';
import { Marker, Popup, Circle, Tooltip } from 'react-leaflet';
import { createNatoDivIcon, parseGeoJSONCoordinates } from './LeafletSetup';

interface UnitFeature {
  id: number | string;
  type: string;
  geometry: {
    type: 'Point';
    coordinates: [number, number]; // [Longitude, Latitude]
  };
  properties: {
    id: number;
    name: string;
    nato_symbol_code: string;
    category_name: string;
    faction: 'BLUFOR' | 'OPFOR' | 'NEUTRAL';
    effective_range_km?: number;
    days_since_update?: number;
    ghost_opacity?: number;
    equipment_summary?: string;
    commander?: string;
  };
}

interface UnitMarkersProps {
  units: UnitFeature[];
}

export const UnitMarkers: React.FC<UnitMarkersProps> = ({ units }) => {
  return (
    <>
      {units.map((unit) => {
        const { geometry, properties } = unit;
        if (!geometry || !geometry.coordinates) return null;

        // INVERSÃO SEGURA DE COORDENADAS GEOJSON: [Lng, Lat] -> [Lat, Lng]
        const [lat, lng] = parseGeoJSONCoordinates(geometry.coordinates);

        // DECAIMENTO TEMPORAL (OPSEC GHOSTING) E ALCANCE MILITAR
        const opacity = properties.ghost_opacity ?? (properties.days_since_update && properties.days_since_update > 2 ? 0.45 : 1.0);
        const rangeKm = properties.effective_range_km ?? 25.0;
        const circleColor = properties.faction === 'OPFOR' ? '#EF4444' : '#00F0FF';

        // CRIAÇÃO DO ÍCONE NATO APP-6 VIA MILSYMBOL
        const natoIcon = createNatoDivIcon(properties.nato_symbol_code, {
          size: 30,
          uniqueDesignation: properties.name,
          opacity: opacity,
        });

        return (
          <React.Fragment key={properties.id || unit.id}>
            {/* CÍRCULO DE ALCANCE DAS ARMAS EXIBIDO PARA TODAS AS UNIDADES */}
            {rangeKm > 0 && (
              <Circle
                center={[lat, lng]}
                radius={rangeKm * 1000} // Converte km em metros
                pathOptions={{
                  color: circleColor,
                  fillColor: circleColor,
                  fillOpacity: 0.08,
                  weight: 1.5,
                  dashArray: '5, 5',
                }}
              >
                <Tooltip permanent direction="top" className="tactical-metric-tooltip">
                  {rangeKm} km
                </Tooltip>
              </Circle>
            )}

            {/* MARCADOR MILITAR NATO */}
            <Marker position={[lat, lng]} icon={natoIcon} opacity={opacity}>
              <Popup className="tactical-popup">
                <div className="unit-popup-content">
                  <h4 style={{ margin: 0, color: circleColor }}>
                    {properties.name}
                  </h4>
                  <p><strong>Ramo:</strong> {properties.category_name}</p>
                  <p><strong>Alcance das Armas:</strong> <span style={{ color: circleColor, fontWeight: 'bold' }}>{rangeKm} km</span></p>
                  <p><strong>OPSEC Status:</strong> {properties.days_since_update || 0} dia(s) decorrido(s) ({(opacity * 100).toFixed(0)}% visibilidade)</p>
                  <p><strong>Equipamento:</strong> {properties.equipment_summary || 'N/A'}</p>
                  <p><strong>Comando:</strong> {properties.commander || 'N/A'}</p>
                </div>
              </Popup>
            </Marker>
          </React.Fragment>
        );
      })}
    </>
  );
};
