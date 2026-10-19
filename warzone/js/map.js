/**
 * WARZONE MAP MODULE (Leaflet + OpenStreetMap + Desenho Temporário)
 * Módulo para inicialização do mapa OpenStreetMap, polígonos de controlo e ferramentas de desenho tático temporário.
 */

const WarzoneMap = (function () {
    let map = null;
    let baseLayers = {};
    let zonesLayerGroup = null;
    let eventsLayerGroup = null;
    let firesLayerGroup = null;
    let temporaryDrawingsLayerGroup = null;

    // Estilos de Polígonos de Controlo Territorial
    const ZONE_STYLES = {
        russia: {
            color: '#FF334B',
            fillColor: '#FF334B',
            fillOpacity: 0.35,
            weight: 2,
            dashArray: '4'
        },
        occupied: {
            color: '#EF4444',
            fillColor: '#EF4444',
            fillOpacity: 0.35,
            weight: 2,
            dashArray: '4'
        },
        ukraine: {
            color: '#FFD700',
            fillColor: '#0057B7',
            fillOpacity: 0.20,
            weight: 2
        },
        sovereign: {
            color: '#FFD700',
            fillColor: '#0057B7',
            fillOpacity: 0.20,
            weight: 2
        },
        ukraine_liberated: {
            color: '#10B981',
            fillColor: '#10B981',
            fillOpacity: 0.25,
            weight: 2
        },
        liberated: {
            color: '#10B981',
            fillColor: '#10B981',
            fillOpacity: 0.25,
            weight: 2
        },
        ukraine_incursion: {
            color: '#00F0FF',
            fillColor: '#0057B7',
            fillOpacity: 0.40,
            weight: 3,
            dashArray: '3, 3'
        },
        incursion: {
            color: '#06B6D4',
            fillColor: '#06B6D4',
            fillOpacity: 0.40,
            weight: 3,
            dashArray: '3, 3'
        },
        contested: {
            color: '#FF9900',
            fillColor: '#FF9900',
            fillOpacity: 0.40,
            weight: 3,
            dashArray: '6, 6'
        },
        active_conflict: {
            color: '#F59E0B',
            fillColor: '#F59E0B',
            fillOpacity: 0.40,
            weight: 3,
            dashArray: '6, 6'
        }
    };

    /**
     * Inicializar o Mapa Leaflet com OpenStreetMap
     */
    function initMap() {
        // Centro na Ucrânia
        map = L.map('map', {
            center: [48.3794, 31.1656],
            zoom: 6,
            zoomControl: false
        });

        // Adicionar Controlo de Zoom no canto inferior direito
        L.control.zoom({ position: 'bottomright' }).addTo(map);

        // CAMADAS DE MAPA BASE OPENSTREETMAP (OSM)
        
        // 1. OpenStreetMap / Esri Dark Tactical (100% Gratuito - Sem API Key)
        baseLayers.osmDark = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
            maxZoom: 16
        });

        // 2. OpenStreetMap Standard (100% Gratuito - Sem API Key)
        baseLayers.osmStandard = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        });

        // 3. Esri World Imagery (Satélite)
        baseLayers.osmSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
            maxZoom: 18
        });

        // Definir camada padrão
        baseLayers.osmDark.addTo(map);

        // Grupos de Camadas Vetoriais
        zonesLayerGroup = L.layerGroup().addTo(map);
        eventsLayerGroup = L.layerGroup().addTo(map);
        unitsLayerGroup = L.layerGroup().addTo(map);
        natoLayerGroup = L.layerGroup().addTo(map);
        firesLayerGroup = L.layerGroup().addTo(map);
        temporaryDrawingsLayerGroup = L.featureGroup().addTo(map);

        // INICIALIZAR FERRAMENTA DE DESENHO TEMPORÁRIO E LEGENDA DE DOMÍNIO
        initDrawingTools();
        initLegendControl();

        console.log('OpenStreetMap inicializado com sucesso.');
    }

    /**
     * Adicionar Legenda Fixa de Domínio no canto do mapa
     */
    function initLegendControl() {
        const legend = L.control({ position: 'bottomleft' });
        legend.onAdd = function () {
            const div = L.DomUtil.create('div', 'tactical-map-legend');
            div.innerHTML = `
                <div class="legend-header"><i class="fa-solid fa-layer-group"></i> LEGENDA DE DOMÍNIO</div>
                <div class="legend-item"><span class="legend-box box-russia"></span> Ocupação Russa</div>
                <div class="legend-item"><span class="legend-box box-contested"></span> Faixa de Conflito Ativo</div>
                <div class="legend-item"><span class="legend-box box-ukraine"></span> Ucrânia Soberana</div>
                <div class="legend-item"><span class="legend-box box-liberated"></span> Áreas Libertadas</div>
                <div class="legend-item"><span class="legend-box box-incursion"></span> Incursão de Kursk</div>
            `;
            return div;
        };
        legend.addTo(map);
    }

    /**
     * Alternar Camadas do Mapa
     */
    function setBaseLayer(layerKey) {
        Object.values(baseLayers).forEach(layer => map.removeLayer(layer));
        if (baseLayers[layerKey]) {
            baseLayers[layerKey].addTo(map);
        }
    }

    /**
     * Inicializar Ferramentas de Desenho Temporário no Mapa (Non-Permanent Drawing)
     */
    function initDrawingTools() {
        if (!map.pm) return;

        // Configuração do Leaflet Geoman para desenho tático
        map.pm.addControls({
            position: 'topleft',
            drawMarker: true,
            drawPolyline: true,
            drawRectangle: true,
            drawPolygon: true,
            drawCircle: true,
            editMode: true,
            dragMode: true,
            cutPolygon: false,
            removalMode: true
        });

        // Personalizar o estilo dos desenhos temporários
        map.pm.setPathOptions({
            color: '#00F0FF',
            fillColor: '#00F0FF',
            fillOpacity: 0.2,
            weight: 3
        });

        /**
         * Calcular métricas de distância (km) e área (km²) de um elemento desenhado
         */
        function calculateShapeMetrics(layer) {
            if (layer instanceof L.Polygon) {
                const latlngs = layer.getLatLngs()[0] || [];
                let perimeterMeters = 0;
                for (let i = 0; i < latlngs.length; i++) {
                    const nextIdx = (i + 1) % latlngs.length;
                    perimeterMeters += latlngs[i].distanceTo(latlngs[nextIdx]);
                }
                const perimKm = (perimeterMeters / 1000).toFixed(2);
                
                let areaSqMeters = 0;
                if (latlngs.length > 2) {
                    for (let i = 0; i < latlngs.length; i++) {
                        const p1 = latlngs[i];
                        const p2 = latlngs[(i + 1) % latlngs.length];
                        areaSqMeters += (p1.lng * p2.lat) - (p2.lng * p1.lat);
                    }
                    areaSqMeters = Math.abs(areaSqMeters) * 111319.5 * 111319.5 * Math.cos(latlngs[0].lat * Math.PI / 180) / 2;
                }
                const areaSqKm = (areaSqMeters / 1000000).toFixed(2);
                return `Área: <strong>${areaSqKm} km²</strong> | Perímetro: <strong>${perimKm} km</strong>`;
            } else if (layer instanceof L.Polyline) {
                const latlngs = layer.getLatLngs();
                let totalMeters = 0;
                for (let i = 0; i < latlngs.length - 1; i++) {
                    totalMeters += latlngs[i].distanceTo(latlngs[i + 1]);
                }
                const distKm = (totalMeters / 1000).toFixed(2);
                return `Distância Total: <strong>${distKm} km</strong>`;
            } else if (layer instanceof L.Circle) {
                const radiusMeters = layer.getRadius();
                const radiusKm = (radiusMeters / 1000).toFixed(2);
                const areaSqKm = (Math.PI * Math.pow(radiusKm, 2)).toFixed(2);
                return `Raio: <strong>${radiusKm} km</strong> | Área: <strong>${areaSqKm} km²</strong>`;
            }
            return '';
        }

        // Quando um novo desenho for criado pelo utilizador
        map.on('pm:create', (e) => {
            const layer = e.layer;
            temporaryDrawingsLayerGroup.addLayer(layer);

            // Calcular distância / área e adicionar Tooltip permanente
            const metricsText = calculateShapeMetrics(layer);
            if (metricsText) {
                layer.bindTooltip(metricsText, {
                    permanent: true,
                    direction: 'top',
                    className: 'tactical-metric-tooltip'
                });
            }

            // Adicionar popup indicando que é um desenho temporário
            layer.bindPopup(`
                <div class="tactical-popup">
                    <h4><i class="fa-solid fa-pen-ruler"></i> Desenho Tático Temporário</h4>
                    <p>${metricsText || 'Elemento criado durante esta sessão de análise.'}</p>
                    <div class="tactical-popup-meta">
                        <span>Status: Não Permanente</span>
                    </div>
                </div>
            `);

            // Atualizar medições se a forma for editada
            layer.on('pm:edit', () => {
                const updatedMetrics = calculateShapeMetrics(layer);
                if (updatedMetrics) {
                    layer.setTooltipContent(updatedMetrics);
                }
            });

            updateDrawingsCount();

            // Tocar efeito sonoro de marcação tática (se ativo)
            if (window.WarzoneApp && WarzoneApp.playSonarSound) {
                WarzoneApp.playSonarSound(600);
            }
        });

        map.on('pm:remove', () => {
            updateDrawingsCount();
        });
    }

    /**
     * Ativar modo de desenho específico via botões do painel lateral
     */
    function enableDrawMode(shapeType) {
        if (!map.pm) return;
        switch (shapeType) {
            case 'Polygon':
                map.pm.enableDraw('Polygon', { snappable: true });
                break;
            case 'Line':
                map.pm.enableDraw('Line', { snappable: true });
                break;
            case 'Circle':
                map.pm.enableDraw('Circle', { snappable: true });
                break;
            case 'Marker':
                map.pm.enableDraw('Marker', { snappable: true });
                break;
        }
    }

    /**
     * Limpar todos os desenhos temporários do mapa
     */
    function clearTemporaryDrawings() {
        temporaryDrawingsLayerGroup.clearLayers();
        updateDrawingsCount();
    }

    /**
     * Atualizar a contagem de elementos desenhados
     */
    function updateDrawingsCount() {
        const count = temporaryDrawingsLayerGroup.getLayers().length;
        const countEl = document.getElementById('activeDrawingsCount');
        if (countEl) {
            countEl.textContent = `${count} elemento(s)`;
        }
    }

    /**
     * Exportar desenhos temporários em formato GeoJSON
     */
    function exportDrawingsGeoJSON() {
        const geojson = temporaryDrawingsLayerGroup.toGeoJSON();
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(geojson, null, 2));
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute("href", dataStr);
        downloadAnchor.setAttribute("download", `desenhos_taticos_warzone_${Date.now()}.geojson`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
    }

    /**
     * Renderizar Polígonos de Controlo Territorial (100% Dinâmico via API/MariaDB GIS)
     */
    function renderZones(zonesData, timelineVal = 2026.7) {
        zonesLayerGroup.clearLayers();

        const zonesToRender = (zonesData && Array.isArray(zonesData) && zonesData.length > 0) ? zonesData : [];

        zonesToRender.forEach(zone => {
            const polygonData = zone.geojson_polygon || zone.boundary;
            if (!polygonData) return;

            const statusKey = zone.control_status || (zone.zone_type ? zone.zone_type.toLowerCase() : 'contested');
            const style = ZONE_STYLES[statusKey] || ZONE_STYLES.contested;
            const geoJsonLayer = L.geoJSON(polygonData, {
                style: {
                    ...style,
                    smoothFactor: 0.1,
                    lineCap: 'round',
                    lineJoin: 'round'
                },
                onEachFeature: (feature, layer) => {
                    const areaText = zone.area_sq_km ? `${Number(zone.area_sq_km).toLocaleString()} km²` : 'N/A';
                    layer.bindPopup(`
                        <div class="tactical-popup">
                            <h4><i class="fa-solid fa-draw-polygon"></i> ${zone.name}</h4>
                            <p>${zone.description || zone.notes || ''}</p>
                            <div class="tactical-popup-meta">
                                <span>Status: <strong>${(statusKey).toUpperCase()}</strong></span>
                                <span>Área: <strong>${areaText}</strong></span>
                            </div>
                        </div>
                    `);
                }
            });

            zonesLayerGroup.addLayer(geoJsonLayer);
        });
    }

    // Guarda o círculo de alcance de armas ativo
    let activeWeaponRangeCircle = null;

    /**
     * Algoritmo de Jittering Geográfico (Dispersão Espacial) para Evitar Sobreposição de Marcadores
     */
    function applyJittering(lat, lon, index, totalCount) {
        if (!totalCount || totalCount <= 1) return [lat, lon];
        const radiusInDegrees = 0.008; // ~800m de dispersão orbital em torno da cidade
        const angle = (index / totalCount) * 2 * Math.PI;
        return [
            lat + radiusInDegrees * Math.sin(angle),
            lon + radiusInDegrees * Math.cos(angle)
        ];
    }

    /**
     * Gerar HTML do Ícone do Marcador baseado na Categoria
     */
    function getCategoryIconHtml(category, severity) {
        let iconClass = 'fa-explosion';
        let colorClass = 'cyan';

        switch (category) {
            case 'missile_strike':
            case 'AIRSTRIKE':
            case 'SHELLING':
                iconClass = 'fa-explosion';
                colorClass = 'red';
                break;
            case 'drone_attack':
            case 'DRONE_ATTACK':
                iconClass = 'fa-plane-triangle-exclamation';
                colorClass = 'amber';
                break;
            case 'ground_combat':
            case 'TROOP_MOVEMENT':
                iconClass = 'fa-person-rifle';
                colorClass = 'red';
                break;
            case 'air_defense':
                iconClass = 'fa-shield-halved';
                colorClass = 'cyan';
                break;
            case 'naval_ops':
            case 'NAVAL_OPS':
                iconClass = 'fa-ship';
                colorClass = 'cyan';
                break;
            case 'infrastructure':
            case 'INFRASTRUCTURE':
                iconClass = 'fa-bolt';
                colorClass = 'amber';
                break;
        }

        return `<div class="marker-pulse marker-${colorClass}"><i class="fa-solid ${iconClass}"></i></div>`;
    }

    /**
     * Renderizar Marcadores de Eventos Táticos (Com Suporte a Heatmap/Zona Difusa para LOW_PRECISION)
     */
    function renderEvents(eventsData) {
        eventsLayerGroup.clearLayers();

        // Mapear contagem de posições repetidas para Jittering
        const posCounts = {};
        eventsData.forEach(evt => {
            const lat = evt.latitude || (evt.geometry ? evt.geometry.coordinates[1] : null);
            const lon = evt.longitude || (evt.geometry ? evt.geometry.coordinates[0] : null);
            if (lat && lon) {
                const key = `${lat.toFixed(3)}_${lon.toFixed(3)}`;
                posCounts[key] = (posCounts[key] || 0) + 1;
            }
        });

        const posIndexes = {};

        eventsData.forEach(event => {
            const props = event.properties || event;
            const coords = event.geometry ? event.geometry.coordinates : [event.longitude, event.latitude];
            if (!coords || !coords[0] || !coords[1]) return;

            const originalLon = coords[0];
            const originalLat = coords[1];
            const posKey = `${originalLat.toFixed(3)}_${originalLon.toFixed(3)}`;
            
            posIndexes[posKey] = (posIndexes[posKey] || 0) + 1;
            const currentIndex = posIndexes[posKey];
            const totalAtPos = posCounts[posKey];

            // Aplicar Jittering espacial se existirem marcadores sobrepostos
            const [dispLat, dispLon] = applyJittering(originalLat, originalLon, currentIndex, totalAtPos);

            const isLowPrecision = (props.precision_class === 'LOW_PRECISION');

            if (isLowPrecision) {
                // Renderizar como Zona Difusa / Heatmap (Raio de 4 km) para evitar falso centro de cidade
                const fuzzyCircle = L.circle([originalLat, originalLon], {
                    radius: 4000,
                    color: '#F59E0B',
                    fillColor: '#F59E0B',
                    fillOpacity: 0.22,
                    weight: 1,
                    dashArray: '4, 4'
                });

                fuzzyCircle.bindPopup(`
                    <div class="tactical-popup">
                        <span class="status-badge" style="background:#B45309;">ZONA DE IMPACTO APROXIMADA (LOW_PRECISION)</span>
                        <h4>${props.title}</h4>
                        <p>${props.description || 'Evento OSINT identificado na área urbana.'}</p>
                    </div>
                `);
                eventsLayerGroup.addLayer(fuzzyCircle);
            } else {
                // Marcador de Alta Precisão (HIGH_PRECISION)
                const iconHtml = getCategoryIconHtml(props.category, props.severity);
                const customIcon = L.divIcon({
                    html: iconHtml,
                    className: 'custom-tactical-marker',
                    iconSize: [30, 30],
                    iconAnchor: [15, 15]
                });

                const marker = L.marker([dispLat, dispLon], { icon: customIcon });

                marker.bindPopup(`
                    <div class="tactical-popup">
                        <span class="status-badge" style="background:#047857;">COORDENADA EXATA (HIGH_PRECISION)</span>
                        <h4>${props.title}</h4>
                        <p><strong>Local:</strong> ${props.location_name || 'Setor Tático'}</p>
                        <p>${props.description || ''}</p>
                        <div class="tactical-popup-meta">
                            <span>Data: ${props.event_date || props.event_timestamp || ''}</span>
                            <span>Fonte: ${props.source_name || props.verification_status || 'OSINT'}</span>
                        </div>
                    </div>
                `);

                eventsLayerGroup.addLayer(marker);
            }
        });
    }

    /**
     * Desenhar ou Alternar Buffer Circular de Alcance Efetivo de Armas
     */
    function toggleWeaponRangeBuffer(lat, lon, rangeKm, unitName) {
        if (activeWeaponRangeCircle) {
            map.removeLayer(activeWeaponRangeCircle);
            activeWeaponRangeCircle = null;
        }

        if (!rangeKm || rangeKm <= 0) return;

        activeWeaponRangeCircle = L.circle([lat, lon], {
            radius: rangeKm * 1000, // em metros
            color: '#3B82F6',
            fillColor: '#3B82F6',
            fillOpacity: 0.12,
            weight: 2,
            dashArray: '6, 6'
        }).addTo(map);

        activeWeaponRangeCircle.bindTooltip(
            `${rangeKm} km`, 
            { permanent: true, direction: 'top', className: 'tactical-metric-tooltip' }
        );
    }

    /**
     * Renderizar Marcadores de Unidades Militares e Círculos de Alcance para Todas as Unidades
     */
    function renderUnits(unitsData) {
        unitsLayerGroup.clearLayers();

        unitsData.forEach(unit => {
            const props = unit.properties || unit;
            const coords = unit.geometry ? unit.geometry.coordinates : [unit.longitude, unit.latitude];
            if (!coords || !coords[0] || !coords[1]) return;

            const lat = coords[1];
            const lon = coords[0];

            // 1. Obter Opacidade de Decaimento Temporal (Ghosting) e Alcance Efetivo
            const ghostOpacity = props.ghost_opacity !== undefined ? props.ghost_opacity : (props.days_since_update > 2 ? 0.45 : 1.0);
            const rangeKm = props.effective_range_km || 25.0;
            const faction = props.faction || 'BLUFOR';
            const circleColor = faction === 'OPFOR' ? '#EF4444' : '#00F0FF';

            // 2. RENDERIZAR CÍRCULO DE ALCANCE DAS ARMAS PARA TODAS AS UNIDADES
            if (rangeKm > 0) {
                const rangeCircle = L.circle([lat, lon], {
                    radius: rangeKm * 1000,
                    color: circleColor,
                    fillColor: circleColor,
                    fillOpacity: 0.08,
                    weight: 1.5,
                    dashArray: '5, 5'
                });

                rangeCircle.bindTooltip(`${rangeKm} km`, {
                    permanent: true,
                    direction: 'top',
                    className: 'tactical-metric-tooltip'
                });

                unitsLayerGroup.addLayer(rangeCircle);
            }

            // 3. RENDERIZAR MARCADOR DA UNIDADE
            const iconHtml = `<div class="unit-badge-marker" style="border-color: ${circleColor}; opacity: ${ghostOpacity};">
                <i class="fa-solid ${props.icon || (faction === 'OPFOR' ? 'fa-shield-cat' : 'fa-shield-halved')}"></i>
            </div>`;

            const customIcon = L.divIcon({
                html: iconHtml,
                className: 'custom-unit-marker',
                iconSize: [36, 36],
                iconAnchor: [18, 18]
            });

            const marker = L.marker([lat, lon], { icon: customIcon, opacity: ghostOpacity });

            marker.bindPopup(`
                <div class="tactical-popup unit-popup">
                    <h4>${props.name}</h4>
                    <p><strong>Ramo:</strong> ${props.category_name || props.branch_name || 'Infantaria'}</p>
                    <p><strong>Alcance das Armas:</strong> <span style="color:${circleColor}; font-weight:bold;">${rangeKm} km</span></p>
                    <p><strong>OPSEC Status:</strong> ${props.days_since_update || 0} dia(s) decorrido(s) (${(ghostOpacity * 100).toFixed(0)}% visibilidade)</p>
                    <p><strong>Equipamento:</strong> ${props.equipment_summary || props.equipment || 'N/A'}</p>
                    <p><strong>Comando:</strong> ${props.commander || 'N/A'}</p>
                </div>
            `);

            unitsLayerGroup.addLayer(marker);
        });
    }

    let isNatoOverlayVisible = false;

    /**
     * Renderizar Camada de Simbologia Militar NATO APP-6D / MIL-STD-2525
     * Suporta todos os Teatros de Operações e Batalhas Históricas (Kyiv, Kharkiv, Kherson, Robotyne, Bakhmut, Kursk, Pokrovsk)
     */
    function renderNatoOverlay(unitsData, timelineVal = 2026.7) {
        natoLayerGroup.clearLayers();

        // Obter unidades dinâmicas recebidas da API/MariaDB
        const activeUnits = (unitsData && Array.isArray(unitsData) && unitsData.length > 0) 
            ? unitsData 
            : (window.WarzoneData ? WarzoneData.getUnits() : []);

        const bluforUnits = activeUnits.filter(u => u.faction === 'BLUFOR' || !u.faction).map(u => ({
            lat: u.latitude,
            lng: u.longitude,
            size: u.echelon || 'II',
            type: u.branch || u.category || 'infantry',
            title: u.name,
            commander: u.commander,
            equipment: u.equipment
        }));

        const opforUnits = activeUnits.filter(u => u.faction === 'OPFOR').map(u => ({
            lat: u.latitude,
            lng: u.longitude,
            size: u.echelon || 'III',
            type: u.branch || u.category || 'cavalry',
            title: u.name,
            commander: u.commander,
            equipment: u.equipment
        }));

        // Calcular centro geográfico dos setores BLUFOR e OPFOR dinamicamente
        let bluforSectorPos = [48.30, 37.08];
        let opforSectorPos = [48.44, 37.62];

        if (bluforUnits.length > 0) {
            const avgLat = bluforUnits.reduce((acc, u) => acc + u.lat, 0) / bluforUnits.length;
            const avgLng = bluforUnits.reduce((acc, u) => acc + u.lng, 0) / bluforUnits.length;
            bluforSectorPos = [avgLat, avgLng];
        }
        if (opforUnits.length > 0) {
            const avgLat = opforUnits.reduce((acc, u) => acc + u.lat, 0) / opforUnits.length;
            const avgLng = opforUnits.reduce((acc, u) => acc + u.lng, 0) / opforUnits.length;
            opforSectorPos = [avgLat, avgLng];
        }

        // FUNÇÃO DE ÍCONE NATO POR BRANCA MILITAR
        function getNatoBranchIcon(type) {
            switch (type) {
                case 'cavalry': return 'fa-truck-monster';
                case 'artillery': return 'fa-crosshairs';
                case 'drones': return 'fa-paper-plane';
                case 'air_defense': return 'fa-shield-halved';
                default: return 'fa-person-rifle';
            }
        }

        // DESENHAR UNIDADES BLUFOR (Azul)
        bluforUnits.forEach(u => {
            const iconClass = getNatoBranchIcon(u.type);
            const html = `
                <div class="nato-app6-symbol blufor">
                    <div class="nato-size-mark">${u.size}</div>
                    <div class="nato-rect-box">
                        <i class="fa-solid ${iconClass}"></i>
                    </div>
                </div>
            `;
            const icon = L.divIcon({
                html: html,
                className: 'custom-nato-marker',
                iconSize: [44, 38],
                iconAnchor: [22, 19]
            });
            const marker = L.marker([u.lat, u.lng], { icon: icon });
            marker.bindPopup(`
                <div class="tactical-popup">
                    <h4><i class="fa-solid fa-shield"></i> ${u.title}</h4>
                    <p><strong>Classificação:</strong> NATO BLUFOR (${u.size})</p>
                    <p><strong>Ramo Tático:</strong> ${u.type.toUpperCase()}</p>
                </div>
            `);
            natoLayerGroup.addLayer(marker);
        });

        // DESENHAR UNIDADES OPFOR (Vermelho Inimigo)
        opforUnits.forEach(u => {
            const iconClass = getNatoBranchIcon(u.type);
            const html = `
                <div class="nato-app6-symbol opfor">
                    <div class="nato-size-mark">${u.size}</div>
                    <div class="nato-diamond-box">
                        <i class="fa-solid ${iconClass}"></i>
                    </div>
                </div>
            `;
            const icon = L.divIcon({
                html: html,
                className: 'custom-nato-marker',
                iconSize: [44, 44],
                iconAnchor: [22, 22]
            });
            const marker = L.marker([u.lat, u.lng], { icon: icon });
            marker.bindPopup(`
                <div class="tactical-popup">
                    <h4><i class="fa-solid fa-diamond"></i> ${u.title}</h4>
                    <p><strong>Classificação:</strong> NATO OPFOR INIMIGO (${u.size})</p>
                    <p><strong>Ramo Tático:</strong> ${u.type.toUpperCase()}</p>
                </div>
            `);
            natoLayerGroup.addLayer(marker);
        });

        // DESENHAR POSTOS DE COMANDO TÁTICO (TCP & AA)
        const commandPosts = [
            { lat: bluforSectorPos[0] + 0.05, lng: bluforSectorPos[1] - 0.08, name: 'TCP ALPHA (HQ)' },
            { lat: opforSectorPos[0] + 0.05, lng: opforSectorPos[1] + 0.08, name: 'OPFOR REGIMENTAL HQ' }
        ];

        commandPosts.forEach(cp => {
            const cpIcon = L.divIcon({
                html: `<div class="nato-cp-badge"><i class="fa-solid fa-flag-checkered"></i> ${cp.name}</div>`,
                className: 'custom-label-marker',
                iconSize: [140, 24],
                iconAnchor: [70, 12]
            });
            natoLayerGroup.addLayer(L.marker([cp.lat, cp.lng], { icon: cpIcon }));
        });

        // DESENHAR EIXO PRINCIPAL DE ATAQUE
        if (axisSabrePoints.length > 0) {
            const axisPolyline = L.polyline(axisSabrePoints, {
                color: '#00F0FF',
                weight: 6,
                dashArray: '12, 6',
                lineCap: 'square'
            });
            natoLayerGroup.addLayer(axisPolyline);

            const axisLabelIcon = L.divIcon({
                html: `<div class="nato-axis-label">${axisName} &rArr;</div>`,
                className: 'custom-label-marker',
                iconSize: [180, 26],
                iconAnchor: [90, 13]
            });
            natoLayerGroup.addLayer(L.marker(axisLabelPos, { icon: axisLabelIcon }));
        }

        // DESENHAR EIXOS SECUNDÁRIOS DE AVANÇO
        secondaryAxes.forEach(pts => {
            natoLayerGroup.addLayer(L.polyline(pts, { color: '#00F0FF', weight: 4, dashArray: '8, 6' }));
        });

        // DESENHAR LINHAS LOA (Limit of Advance)
        if (loaPoints.length > 0) {
            const loaPolyline = L.polyline(loaPoints, { color: '#FFF', weight: 4, dashArray: '4, 8' });
            natoLayerGroup.addLayer(loaPolyline);
        }
        loaLabels.forEach(lbl => {
            const loaIcon = L.divIcon({ html: `<div class="nato-line-label">${lbl.text}</div>`, className: 'custom-label-marker' });
            natoLayerGroup.addLayer(L.marker([lbl.lat, lbl.lng], { icon: loaIcon }));
        });

        // DESENHAR LINHAS PL (Phase Line / FSCL)
        if (plPoints.length > 0) {
            natoLayerGroup.addLayer(L.polyline(plPoints, { color: '#FFD700', weight: 2, dashArray: '6, 6' }));
            const plLabel = L.divIcon({ html: `<div class="nato-line-label pl">${plName}</div>`, className: 'custom-label-marker' });
            natoLayerGroup.addLayer(L.marker(plLabelPos, { icon: plLabel }));
        }

        // DESENHAR OBJETIVOS TÁTICOS (OBJ)
        objectives.forEach(obj => {
            const circle = L.circle([obj.lat, obj.lng], {
                radius: 1500,
                color: '#FFF',
                fillColor: '#FFF',
                fillOpacity: 0.12,
                weight: 2
            });
            natoLayerGroup.addLayer(circle);

            const labelIcon = L.divIcon({
                html: `<div class="nato-obj-label"><div class="obj-circle"></div> ${obj.name}</div>`,
                className: 'custom-label-marker',
                iconSize: [180, 30],
                iconAnchor: [0, 15]
            });
            natoLayerGroup.addLayer(L.marker([obj.lat, obj.lng + 0.025], { icon: labelIcon }));
        });

        // RÓTULOS DE SETOR
        const bluforSectorLabel = L.divIcon({ html: `<div class="nato-sector-label blufor">BLUFOR SECTOR</div>`, className: 'custom-label-marker' });
        const opforSectorLabel = L.divIcon({ html: `<div class="nato-sector-label opfor">OPFOR SECTOR</div>`, className: 'custom-label-marker' });
        natoLayerGroup.addLayer(L.marker(bluforSectorPos, { icon: bluforSectorLabel }));
        natoLayerGroup.addLayer(L.marker(opforSectorPos, { icon: opforSectorLabel }));

        isNatoOverlayVisible = true;
    }

    /**
     * Alternar Visibilidade da Camada NATO APP-6
     */
    function toggleNatoOverlay(timelineVal = 2026.7) {
        if (isNatoOverlayVisible) {
            natoLayerGroup.clearLayers();
            isNatoOverlayVisible = false;
        } else {
            renderNatoOverlay(timelineVal);
        }
        return isNatoOverlayVisible;
    }

    /**
     * Focar mapa em coordenadas específicas
     */
    function flyToLocation(lat, lng, zoom = 10) {
        if (map) {
            map.flyTo([lat, lng], zoom, { duration: 1.5 });
        }
    }

    return {
        initMap,
        setBaseLayer,
        enableDrawMode,
        clearTemporaryDrawings,
        exportDrawingsGeoJSON,
        renderZones,
        renderEvents,
        renderUnits,
        toggleWeaponRangeBuffer,
        renderNatoOverlay,
        toggleNatoOverlay,
        flyToLocation
    };
})();
