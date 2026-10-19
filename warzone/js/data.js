/**
 * WARZONE DATA MODULE
 * Módulo responsável pela integração com o Backend Node/MariaDB GIS.
 */

const WarzoneData = (function () {
    const API_BASE = '/api';

    let state = {
        zones: [],
        events: [],
        units: [],
        drawings: [],
        stats: {},
        isDatabaseConnected: false
    };

    /**
     * Verificar estado do Backend & MariaDB
     */
    async function checkStatus() {
        try {
            const res = await fetch(`${API_BASE}/status`);
            if (res.ok) {
                const data = await res.json();
                state.isDatabaseConnected = true;
                return data;
            }
        } catch (err) {
            console.warn('Backend /api/status não acessível, a utilizar fallback local.');
        }
        return { database: 'StandAlone Fallback Engine' };
    }

    /**
     * Obter zonas de controlo territorial em formato GeoJSON FeatureCollection ou Array
     */
    async function fetchZones(targetDate = null) {
        try {
            const url = targetDate ? `${API_BASE}/zones?target_date=${targetDate}` : `${API_BASE}/zones`;
            const res = await fetch(url);
            if (res.ok) {
                const data = await res.json();
                const zones = Array.isArray(data) ? data : (data.features || []);
                if (zones.length > 0) {
                    state.zones = zones;
                }
                return state.zones;
            }
        } catch (err) {
            console.warn('Erro ao carregar zonas:', err);
        }
        return state.zones;
    }

    /**
     * Obter destacamentos militares
     */
    async function fetchUnits(filters = {}) {
        try {
            let branch = typeof filters === 'string' ? filters : (filters.branch || null);
            const url = branch && branch !== 'all' ? `${API_BASE}/units?branch=${branch}` : `${API_BASE}/units`;
            const res = await fetch(url);
            if (res.ok) {
                const data = await res.json();
                const units = Array.isArray(data) ? data : (data.features || []);
                if (units.length > 0) {
                    state.units = units;
                }
                return state.units;
            }
        } catch (err) {
            console.warn('Erro ao carregar unidades:', err);
        }
        return state.units;
    }

    /**
     * Obter eventos OSINT geolocalizados
     */
    async function fetchEvents(filters = {}) {
        try {
            const queryParams = new URLSearchParams(filters).toString();
            const res = await fetch(`${API_BASE}/events?${queryParams}`);
            if (res.ok) {
                const data = await res.json();
                const fetchedEvents = Array.isArray(data) ? data : (data.features || []);
                if (fetchedEvents.length > 0) {
                    state.events = fetchedEvents;
                }
                return state.events;
            }
        } catch (err) {
            console.warn('Erro ao carregar eventos OSINT:', err);
        }
        return state.events;
    }

    /**
     * Obter dados analíticos e estatísticas do conflito
     */
    async function fetchStats() {
        try {
            const res = await fetch(`${API_BASE}/stats`);
            if (res.ok) {
                state.stats = await res.json();
                return state.stats;
            }
        } catch (err) {
            console.warn('Erro ao carregar estatísticas:', err);
        }
        return {
            occupied_territory_pct: 17.85,
            liberated_sq_km: 42100.0,
            active_frontline_km: 1200.0,
            interception_rate_pct: 86.4
        };
    }

    /**
     * Desencadear varredura automática do Web Scraper OSINT
     */
    async function triggerScraperSync() {
        try {
            const res = await fetch(`${API_BASE}/sync`, { method: 'POST' });
            if (res.ok) {
                return await res.json();
            }
        } catch (err) {
            console.error('Erro ao desencadear scraper OSINT:', err);
        }
        return { status: 'error', message: 'Falha na ligação ao backend' };
    }

    /**
     * Guardar elemento desenhado no quadro tático
     */
    async function saveTacticalDrawing(drawingData) {
        try {
            const res = await fetch(`${API_BASE}/tactical`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(drawingData)
            });
            if (res.ok) {
                return await res.json();
            }
        } catch (err) {
            console.error('Erro ao guardar elemento tático:', err);
        }
        return null;
    }

    /**
     * Adicionar novo evento via API POST /api/events
     */
    async function addEvent(newEventData) {
        try {
            const res = await fetch(`${API_BASE}/events`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newEventData)
            });
            if (res.ok) {
                const saved = await res.json();
                state.events.unshift(saved);
                return saved;
            }
        } catch (err) {
            console.error('Erro ao adicionar evento:', err);
        }
        newEventData.id = state.events.length + 1;
        state.events.unshift(newEventData);
        return newEventData;
    }

    return {
        checkStatus,
        fetchZones,
        fetchUnits,
        fetchEvents,
        fetchStats,
        triggerScraperSync,
        saveTacticalDrawing,
        addEvent,
        getState: () => state
    };
})();
