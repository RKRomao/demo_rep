/**
 * WARZONE APP MODULE (Orquestrador Principal)
 * Conecta o motor de dados, o mapa OpenStreetMap, os desenhos temporários, o painel tático e os gráficos.
 */

const WarzoneApp = (function () {
    let audioEnabled = true;
    let audioCtx = null;
    let activeCategory = 'all';
    let searchQuery = '';

    /**
     * Inicializar a aplicação
     */
    async function init() {
        console.log('Inicializando WARZONE Tracker...');

        // 1. Inicializar Mapa OpenStreetMap
        WarzoneMap.initMap();

        // 2. Inicializar Relógio UTC & Temporizador de Auto-Scraping (5 Min)
        startUTCClock();
        startSyncCountdown();

        // 3. Verificar estado do Backend & MariaDB
        const status = await WarzoneData.checkStatus();
        updateDBBadge(status);

        // 4. Carregar Dados de Zonas, Eventos e Unidades Militares
        const zones = await WarzoneData.fetchZones();
        WarzoneMap.renderZones(zones);

        const events = await WarzoneData.fetchEvents();
        WarzoneMap.renderEvents(events);
        renderEventFeed(events);

        const units = await WarzoneData.fetchUnits();
        WarzoneMap.renderUnits(units);
        renderUnitFeed(units);

        const stats = await WarzoneData.fetchStats();
        updateStatsUI(stats);

        // 5. Inicializar Gráficos & Linha do Tempo
        WarzoneCharts.initCharts(events);
        WarzoneTimeline.init();

        // 6. Registar Listeners da Interface
        bindEventListeners();

        console.log('WARZONE Tracker totalmente operacional.');
    }

    /**
     * Atualizar relógio UTC no cabeçalho
     */
    function startUTCClock() {
        const clockEl = document.getElementById('currentTimeUTC');
        if (!clockEl) return;

        function updateClock() {
            const now = new Date();
            const utcStr = now.toISOString().substring(11, 19);
            clockEl.innerHTML = `<i class="fa-regular fa-clock"></i> ${utcStr} UTC`;
        }
        updateClock();
        setInterval(updateClock, 1000);
    }

    let syncSecondsLeft = 300;
    /**
     * Temporizador da Contagem Decrescente de 5 Minutos (Auto Scraping OSINT)
     */
    function startSyncCountdown() {
        const countdownEl = document.getElementById('syncCountdownText');
        if (!countdownEl) return;

        setInterval(async () => {
            syncSecondsLeft--;
            if (syncSecondsLeft <= 0) {
                syncSecondsLeft = 300;
                await triggerWebSync();
            }

            const mins = Math.floor(syncSecondsLeft / 60);
            const secs = syncSecondsLeft % 60;
            const minStr = mins < 10 ? `0${mins}` : `${mins}`;
            const secStr = secs < 10 ? `0${secs}` : `${secs}`;
            countdownEl.textContent = `${minStr}:${secStr}`;
        }, 1000);
    }

    /**
     * Executar varredura forçada de Web Scraping OSINT
     */
    function triggerWebSync() {
        const syncBtn = document.getElementById('btnForceSync');
        if (syncBtn) {
            syncBtn.disabled = true;
            syncBtn.innerHTML = `<i class="fa-solid fa-rotate fa-spin"></i> A varrer fontes...`;
        }

        fetch('/api/sync', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                playSonarSound(950);
                return applyFilters();
            })
            .catch(err => console.error('Erro na sincronização de web scraping:', err))
            .finally(() => {
                if (syncBtn) {
                    syncBtn.disabled = false;
                    syncBtn.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> Varrer Fontes Agora`;
                }
            });
    }

    /**
     * Atualizar badge de estado MariaDB
     */
    function updateDBBadge(status) {
        const badgeEl = document.getElementById('dbStatusBadge');
        if (!badgeEl) return;

        if (status.database && status.database.includes('MariaDB (Conectado)')) {
            badgeEl.className = 'status-badge db-badge';
            badgeEl.innerHTML = `<i class="fa-solid fa-database"></i> MARIADB CONECTADO`;
        } else {
            badgeEl.className = 'status-badge';
            badgeEl.innerHTML = `<i class="fa-solid fa-server"></i> MOTOR IN-MEMORY`;
        }
    }

    /**
     * Efeito Sonoro de Sonar Tático (Web Audio API)
     */
    function playSonarSound(freq = 440) {
        if (!audioEnabled) return;
        try {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(freq / 2, audioCtx.currentTime + 0.15);

            gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.15);

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            osc.start();
            osc.stop(audioCtx.currentTime + 0.15);
        } catch (e) {
            // Ignorar erros de suporte áudio
        }
    }

    /**
     * Renderizar cartões do feed de eventos no painel tático
     */
    function renderEventFeed(events) {
        const feedListEl = document.getElementById('eventFeedList');
        if (!feedListEl) return;

        if (!events || events.length === 0) {
            feedListEl.innerHTML = '<div class="no-events"><p>Nenhum evento encontrado para os filtros selecionados.</p></div>';
            return;
        }

        let html = '';
        events.forEach(evt => {
            const props = evt.properties || evt;
            const coords = evt.geometry ? evt.geometry.coordinates : [evt.longitude, evt.latitude];
            const lat = coords ? coords[1] : (evt.latitude || 0);
            const lng = coords ? coords[0] : (evt.longitude || 0);
            const title = props.title || 'Evento OSINT';
            const category = props.category || 'SHELLING';
            const locationName = props.location_name || props.source_name || 'Setor Tático';
            const dateStr = props.event_date || props.event_timestamp || 'Hoje';
            const severity = props.severity || 'high';

            html += `
                <div class="event-card severity-${severity}" data-lat="${lat}" data-lng="${lng}">
                    <div class="event-card-header">
                        <span class="event-category-badge"><i class="fa-solid fa-crosshairs"></i> ${formatCategoryName(category)}</span>
                        <span class="event-date">${dateStr}</span>
                    </div>
                    <div class="event-title">${title}</div>
                    <div class="event-location"><i class="fa-solid fa-location-dot"></i> ${locationName}</div>
                </div>
            `;
        });

        feedListEl.innerHTML = html;

        // Adicionar listener de clique para voar no mapa até ao evento
        feedListEl.querySelectorAll('.event-card').forEach(card => {
            card.addEventListener('click', () => {
                const lat = parseFloat(card.getAttribute('data-lat'));
                const lng = parseFloat(card.getAttribute('data-lng'));
                if (lat && lng) {
                    WarzoneMap.flyToLocation(lat, lng, 10);
                    playSonarSound(800);
                }
            });
        });
    }

    /**
     * Renderizar lista de cartões de Unidades Militares e Brigadas com Brasões
     */
    function renderUnitFeed(units) {
        const unitListEl = document.getElementById('unitFeedList');
        if (!unitListEl) return;

        if (!units || units.length === 0) {
            unitListEl.innerHTML = '<div class="no-events"><p>Nenhuma unidade encontrada para a categoria selecionada.</p></div>';
            return;
        }

        let html = '';
        units.forEach(unit => {
            const props = unit.properties || unit;
            const coords = unit.geometry ? unit.geometry.coordinates : [unit.longitude, unit.latitude];
            const lat = coords ? coords[1] : (unit.latitude || 0);
            const lng = coords ? coords[0] : (unit.longitude || 0);
            const name = props.name || 'Destacamento Militar';
            const branchName = props.category_name || props.branch_name || 'Infantaria';
            const equipment = props.equipment_summary || props.equipment || 'N/A';
            const faction = props.faction || 'BLUFOR';
            const color = faction === 'OPFOR' ? '#EF4444' : '#00F0FF';
            const icon = props.icon || (faction === 'OPFOR' ? 'fa-shield-cat' : 'fa-shield-halved');

            html += `
                <div class="unit-card" data-lat="${lat}" data-lng="${lng}">
                    <div class="unit-card-header">
                        <div class="unit-crest-badge" style="border-color: ${color}">
                            <i class="fa-solid ${icon}"></i>
                        </div>
                        <div class="unit-header-meta">
                            <span class="unit-branch-tag" style="color: ${color}">${branchName}</span>
                            <span class="unit-name">${name}</span>
                        </div>
                    </div>
                    <div class="unit-sector"><i class="fa-solid fa-location-dot"></i> Pos: [${lat.toFixed(2)}, ${lng.toFixed(2)}]</div>
                    <div class="unit-equip"><i class="fa-solid fa-gears"></i> Equip: ${equipment}</div>
                    <button class="tactical-btn btn-sm fly-unit-btn"><i class="fa-solid fa-crosshairs"></i> Ver Posição no Mapa</button>
                </div>
            `;
        });

        unitListEl.innerHTML = html;

        unitListEl.querySelectorAll('.unit-card').forEach(card => {
            card.addEventListener('click', () => {
                const lat = parseFloat(card.getAttribute('data-lat'));
                const lng = parseFloat(card.getAttribute('data-lng'));
                if (lat && lng) {
                    WarzoneMap.flyToLocation(lat, lng, 11);
                    playSonarSound(850);
                }
            });
        });
    }

    /**
     * Formatar nome legível da categoria
     */
    function formatCategoryName(cat) {
        const names = {
            missile_strike: 'Ataque de Míssil',
            AIRSTRIKE: 'Ataque Aéreo',
            drone_attack: 'Ataque de Drone',
            DRONE_ATTACK: 'Ataque de Drone',
            ground_combat: 'Combate Terrestre',
            TROOP_MOVEMENT: 'Movimento de Tropas',
            SHELLING: 'Bombardeamento / Artilharia',
            air_defense: 'Defesa Aérea',
            naval_ops: 'Operação Naval',
            NAVAL_OPS: 'Operação Naval',
            infrastructure: 'Infraestrutura',
            INFRASTRUCTURE: 'Infraestrutura'
        };
        return names[cat] || cat;
    }

    /**
     * Atualizar valores no painel de estatísticas
     */
    function updateStatsUI(stats) {
        if (stats.occupied_territory_pct) {
            document.getElementById('statOccupiedPct').textContent = `${stats.occupied_territory_pct}%`;
        }
        if (stats.liberated_sq_km) {
            document.getElementById('statLiberatedKm').textContent = `${stats.liberated_sq_km.toLocaleString()} km²`;
        }
        if (stats.active_frontline_km) {
            document.getElementById('statFrontlineKm').textContent = `${stats.active_frontline_km.toLocaleString()} km`;
        }
        if (stats.interception_rate_pct) {
            document.getElementById('statInterceptionRate').textContent = `${stats.interception_rate_pct}%`;
        }
    }

    /**
     * Registar todos os Event Listeners da Interface
     */
    function bindEventListeners() {
        // FORÇAR VARREDURA OSINT EM TEMPO REAL
        const forceSyncBtn = document.getElementById('btnForceSync');
        if (forceSyncBtn) {
            forceSyncBtn.addEventListener('click', triggerWebSync);
        }

        // Alternar Gaveta Tática
        const toggleDrawerBtn = document.getElementById('toggleDrawerBtn');
        const drawerEl = document.getElementById('tacticalDrawer');
        if (toggleDrawerBtn && drawerEl) {
            toggleDrawerBtn.addEventListener('click', () => {
                drawerEl.classList.toggle('collapsed');
                toggleDrawerBtn.classList.toggle('active');
                playSonarSound(500);
            });
        }

        // Alternar Áudio
        const audioBtn = document.getElementById('toggleAudioBtn');
        if (audioBtn) {
            audioBtn.addEventListener('click', () => {
                audioEnabled = !audioEnabled;
                audioBtn.innerHTML = audioEnabled ? '<i class="fa-solid fa-volume-high"></i> Sonar: ON' : '<i class="fa-solid fa-volume-xmark"></i> Sonar: OFF';
                if (audioEnabled) playSonarSound(660);
            });
        }

        // Navegação de Abas da Gaveta
        const tabBtns = document.querySelectorAll('.drawer-tabs .tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.getAttribute('data-tab');
                tabBtns.forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));

                btn.classList.add('active');
                const targetEl = document.getElementById(targetTab);
                if (targetEl) targetEl.classList.add('active');

                playSonarSound(550);
            });
        });

        // Alternar Camadas do OpenStreetMap
        document.getElementById('btnOsmDark').addEventListener('click', function () {
            setActiveLayerBtn(this);
            WarzoneMap.setBaseLayer('osmDark');
        });
        document.getElementById('btnOsmStandard').addEventListener('click', function () {
            setActiveLayerBtn(this);
            WarzoneMap.setBaseLayer('osmStandard');
        });
        document.getElementById('btnOsmSatellite').addEventListener('click', function () {
            setActiveLayerBtn(this);
            WarzoneMap.setBaseLayer('osmSatellite');
        });

        // Alternar Camada NATO APP-6
        const natoBtn = document.getElementById('btnToggleNatoOverlay');
        const natoModeBtn = document.getElementById('btnToggleNatoMode');

        if (natoBtn) {
            natoBtn.addEventListener('click', function () {
                const isActive = WarzoneMap.toggleNatoOverlay();
                this.classList.toggle('active', isActive);
                if (isActive) WarzoneMap.flyToLocation(48.25, 37.45, 10);
                playSonarSound(800);
            });
        }

        if (natoModeBtn) {
            natoModeBtn.addEventListener('click', function () {
                const isActive = WarzoneMap.toggleNatoOverlay();
                this.classList.toggle('active', isActive);
                if (natoBtn) natoBtn.classList.toggle('active', isActive);
                if (isActive) WarzoneMap.flyToLocation(48.25, 37.45, 10);
                playSonarSound(800);
            });
        }

        function setActiveLayerBtn(btn) {
            document.querySelectorAll('.map-layer-controls .layer-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            playSonarSound(700);
        }

        // FERRAMENTAS DE DESENHO TEMPORÁRIO NO MAPA
        document.getElementById('toolDrawPoly').addEventListener('click', () => WarzoneMap.enableDrawMode('Polygon'));
        document.getElementById('toolDrawLine').addEventListener('click', () => WarzoneMap.enableDrawMode('Line'));
        document.getElementById('toolDrawCircle').addEventListener('click', () => WarzoneMap.enableDrawMode('Circle'));
        document.getElementById('toolDrawMarker').addEventListener('click', () => WarzoneMap.enableDrawMode('Marker'));

        document.getElementById('clearDrawingsBtn').addEventListener('click', () => {
            if (confirm('Deseja limpar todos os desenhos temporários do mapa?')) {
                WarzoneMap.clearTemporaryDrawings();
                playSonarSound(300);
            }
        });

        document.getElementById('exportDrawingsBtn').addEventListener('click', () => {
            WarzoneMap.exportDrawingsGeoJSON();
        });

        // OPERAÇÕES HISTÓRICAS (TIME TRAVEL & MAP FLY)
        document.querySelectorAll('.op-card').forEach(card => {
            card.addEventListener('click', () => {
                const dateVal = parseFloat(card.getAttribute('data-date'));
                const lat = parseFloat(card.getAttribute('data-lat'));
                const lng = parseFloat(card.getAttribute('data-lng'));

                if (dateVal && WarzoneTimeline.setTimelineDate) {
                    WarzoneTimeline.setTimelineDate(dateVal);
                }
                if (lat && lng) {
                    WarzoneMap.flyToLocation(lat, lng, 9);
                    playSonarSound(850);
                }
            });
        });

        // FILTROS DE CATEGORIA E BUSCA
        const categoryChips = document.querySelectorAll('#categoryChips .chip');
        categoryChips.forEach(chip => {
            chip.addEventListener('click', async () => {
                categoryChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                activeCategory = chip.getAttribute('data-cat');
                playSonarSound(600);
                await applyFilters();
            });
        });

        // FILTROS DE CATEGORIA DE UNIDADES MILITARES
        const unitCategoryChips = document.querySelectorAll('#unitCategoryChips .chip');
        unitCategoryChips.forEach(chip => {
            chip.addEventListener('click', async () => {
                unitCategoryChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                const branch = chip.getAttribute('data-unit-cat');
                playSonarSound(650);
                const filteredUnits = await WarzoneData.fetchUnits({ branch: branch });
                WarzoneMap.renderUnits(filteredUnits);
                renderUnitFeed(filteredUnits);
            });
        });

        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', async (e) => {
                searchQuery = e.target.value;
                await applyFilters();
            });
        }

        // MODAL ADICIONAR EVENTO
        const modal = document.getElementById('addEventModal');
        const openModalBtn = document.getElementById('openAddEventModalBtn');
        const closeModalBtn = document.getElementById('closeAddEventModalBtn');
        const cancelBtn = document.getElementById('cancelAddEventBtn');
        const form = document.getElementById('addEventForm');

        if (openModalBtn) openModalBtn.addEventListener('click', () => { modal.classList.add('active'); playSonarSound(650); });
        if (closeModalBtn) closeModalBtn.addEventListener('click', () => modal.classList.remove('active'));
        if (cancelBtn) cancelBtn.addEventListener('click', () => modal.classList.remove('active'));

        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const newEvent = {
                    title: document.getElementById('eventTitleInput').value,
                    category: document.getElementById('eventCategorySelect').value,
                    severity: document.getElementById('eventSeveritySelect').value,
                    latitude: document.getElementById('eventLatInput').value,
                    longitude: document.getElementById('eventLngInput').value,
                    location_name: document.getElementById('eventLocationInput').value,
                    description: document.getElementById('eventDescInput').value,
                    event_date: new Date().toISOString().split('T')[0]
                };

                const saved = await WarzoneData.addEvent(newEvent);
                modal.classList.remove('active');
                form.reset();

                // Atualizar Mapa e Feed
                const allEvents = WarzoneData.getState().events;
                WarzoneMap.renderEvents(allEvents);
                renderEventFeed(allEvents);
                WarzoneCharts.updateCharts(allEvents);

                WarzoneMap.flyToLocation(saved.latitude, saved.longitude, 9);
                playSonarSound(900);
            });
        }
    }

    /**
     * Reagir a alterações na Linha do Tempo (Time Machine Slider)
     */
    async function onTimelineChange(val) {
        activeTimelineVal = val;

        const allEvents = WarzoneData.getState().events || [];
        let filteredEvents = [];

        if (val < 2022.3) {
            // Era 1: Fevereiro / Março 2022
            filteredEvents = allEvents.filter(e => !e.event_date || e.event_date <= '2022-04-30');
        } else if (val < 2022.9) {
            // Era 2 & 3: Abril - Outubro 2022
            filteredEvents = allEvents.filter(e => !e.event_date || e.event_date <= '2022-11-30');
        } else if (val < 2024.0) {
            // Era 4: Ano 2023
            filteredEvents = allEvents.filter(e => !e.event_date || e.event_date <= '2023-12-31');
        } else {
            // Era 5: 2024 - 2026 (Todos)
            filteredEvents = allEvents;
        }

        const allZones = WarzoneData.getState().zones || [];
        WarzoneMap.renderZones(allZones, val);
        WarzoneMap.renderEvents(filteredEvents);
        WarzoneMap.renderNatoOverlay(val);
        renderEventFeed(filteredEvents);
        WarzoneCharts.updateCharts(filteredEvents);
    }

    /**
     * Aplicar filtros de busca e categoria
     */
    async function applyFilters() {
        const events = await WarzoneData.fetchEvents({
            category: activeCategory,
            search: searchQuery
        });
        WarzoneMap.renderEvents(events);
        renderEventFeed(events);
        WarzoneCharts.updateCharts(events);
    }

    return {
        init,
        playSonarSound,
        onTimelineChange
    };
})();

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', WarzoneApp.init);
