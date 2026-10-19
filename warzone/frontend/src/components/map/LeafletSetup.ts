import L from 'leaflet';
import ms from 'milsymbol';

// 1. CORREÇÃO DO BUG NATIVO DO LEAFLET COM VITE / WEBPACK
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

export function setupLeafletIcons() {
  delete (L.Icon.Default.prototype as any)._getIconUrl;

  L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2x,
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
  });
}

// 2. UTILITÁRIO DE INVERSÃO SEGURA DE COORDENADAS GEOJSON [Lng, Lat] -> [Lat, Lng]
export function parseGeoJSONCoordinates(coordinates: [number, number]): [number, number] {
  if (!coordinates || coordinates.length < 2) return [0, 0];
  const [lng, lat] = coordinates;
  // Retorna no formato exigido pelo Leaflet: [Latitude, Longitude]
  return [lat, lng];
}

// 3. INTEGRAÇÃO MILSYMBOL -> LEAFLET DIVICON (Simbologia NATO APP-6D / MIL-STD-2525)
export function createNatoDivIcon(
  natoCode: string,
  options: { size?: number; uniqueDesignation?: string; opacity?: number } = {}
): L.DivIcon {
  const symbol = new ms.Symbol(natoCode || 'SFGPU------', {
    size: options.size || 28,
    uniqueDesignation: options.uniqueDesignation || '',
    fill: true,
    stroke: true,
  });

  const anchor = symbol.getAnchor();
  const size = symbol.getSize();

  const svgHtml = symbol.asSVG();

  return L.divIcon({
    html: `<div style="opacity: ${options.opacity ?? 1.0}; transform: translate(-50%, -50%);">${svgHtml}</div>`,
    className: 'nato-milsymbol-icon',
    iconSize: [size.width, size.height],
    iconAnchor: [anchor.x, anchor.y],
  });
}
