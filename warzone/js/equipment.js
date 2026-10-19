/**
 * WARZONE EQUIPMENT HUB MODULE
 * Gestor do Catálogo Tático de Armamento, Viaturas e Sistemas Destacados
 */

document.addEventListener('DOMContentLoaded', () => {
    EquipmentHub.init();
});

const EquipmentHub = (function () {
    let state = {
        items: [],
        activeFaction: 'all',
        activeCategory: 'all',
        searchQuery: ''
    };

    /**
     * Inicializar o Módulo
     */
    async function init() {
        console.log('Inicializando WARZONE Equipment Hub...');
        bindEvents();
        await loadEquipment();
    }

    /**
     * Registar Event Listeners
     */
    function bindEvents() {
        // Campo de Pesquisa
        const searchInput = document.getElementById('eqSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                state.searchQuery = e.target.value;
                render();
            });
        }

        // Filtros de Fação
        const factionBtns = document.querySelectorAll('.faction-filter-btn');
        factionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                factionBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.activeFaction = btn.getAttribute('data-faction');
                render();
            });
        });

        // Filtros de Categoria
        const categoryBtns = document.querySelectorAll('.category-filter-btn');
        categoryBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                categoryBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.activeCategory = btn.getAttribute('data-category');
                render();
            });
        });
    }

    /**
     * Carregar Dados do Armamento via API REST
     */
    async function loadEquipment() {
        const gridEl = document.getElementById('equipmentGrid');
        if (gridEl) {
            gridEl.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> A carregar catálogo de armamento tático...</div>';
        }

        try {
            const res = await fetch('/api/equipment');
            if (res.ok) {
                state.items = await res.json();
                updateStatsOverview();
                render();
            }
        } catch (err) {
            console.error('Erro ao carregar catálogo de armamento:', err);
            if (gridEl) {
                gridEl.innerHTML = '<div class="no-events"><p>Erro ao conectar à API de equipamento.</p></div>';
            }
        }
    }

    /**
     * Atualizar Barra de Estatísticas Globais
     */
    function updateStatsOverview() {
        const totalEl = document.getElementById('statTotalEquipment');
        const rangeEl = document.getElementById('statMaxRange');
        const sectorsEl = document.getElementById('statActiveSectors');

        if (totalEl) totalEl.textContent = state.items.length;
        
        if (rangeEl && state.items.length > 0) {
            const maxRange = Math.max(...state.items.map(i => i.effective_range_km || 0));
            rangeEl.textContent = `${maxRange} km`;
        }

        if (sectorsEl && state.items.length > 0) {
            const sectors = new Set(state.items.map(i => i.location_name));
            sectorsEl.textContent = sectors.size;
        }
    }

    /**
     * Filtrar e Renderizar Grelha de Armamento
     */
    function render() {
        const gridEl = document.getElementById('equipmentGrid');
        if (!gridEl) return;

        let filtered = [...state.items];

        if (state.activeFaction !== 'all') {
            filtered = filtered.filter(item => item.faction === state.activeFaction);
        }

        if (state.activeCategory !== 'all') {
            filtered = filtered.filter(item => item.category === state.activeCategory);
        }

        if (state.searchQuery) {
            const q = state.searchQuery.toLowerCase();
            filtered = filtered.filter(item =>
                item.name.toLowerCase().includes(q) ||
                item.origin_country.toLowerCase().includes(q) ||
                item.main_weapon.toLowerCase().includes(q) ||
                item.deployed_units.toLowerCase().includes(q) ||
                item.location_name.toLowerCase().includes(q)
            );
        }

        if (filtered.length === 0) {
            gridEl.innerHTML = '<div class="no-events" style="grid-column: 1/-1;"><p><i class="fa-solid fa-shield-exclamation"></i> Nenhum equipamento encontrado para os filtros selecionados.</p></div>';
            return;
        }

        let html = '';
        filtered.forEach(item => {
            const factionClass = item.faction === 'OPFOR' ? 'faction-opfor' : 'faction-blufor';
            const factionBadgeClass = item.faction === 'OPFOR' ? 'opfor' : 'blufor';
            const factionIcon = item.faction === 'OPFOR' ? 'fa-skull' : 'fa-shield-halved';
            const icon = item.icon || 'fa-tank';
            const imageUrl = item.image_url || 'assets/equipment/bradley.jpg';

            html += `
                <div class="eq-card ${factionClass}">
                    <div class="eq-card-image-wrap">
                        <img src="${imageUrl}" alt="${item.name}" class="eq-card-image" onerror="this.src='https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=600&auto=format&fit=crop&q=60'">
                    </div>
                    <div class="eq-card-header">
                        <div class="eq-title-wrap">
                            <h2><i class="fa-solid ${icon}"></i> ${item.name}</h2>
                            <div class="eq-category-tag">${item.category_name}</div>
                        </div>
                        <div class="eq-faction-badge ${factionBadgeClass}">
                            <i class="fa-solid ${factionIcon}"></i> ${item.faction}
                        </div>
                    </div>

                    <div class="eq-card-body">
                        <div class="eq-meta-grid">
                            <div class="eq-meta-item">
                                <span class="label">Origem</span>
                                <span class="value">${item.origin_flag} ${item.origin_country}</span>
                            </div>
                            <div class="eq-meta-item">
                                <span class="label">Alcance Efetivo</span>
                                <span class="value">${item.effective_range_km} km</span>
                            </div>
                            <div class="eq-meta-item" style="grid-column: span 2;">
                                <span class="label">Armamento Principal</span>
                                <span class="value">${item.main_weapon}</span>
                            </div>
                            <div class="eq-meta-item" style="grid-column: span 2;">
                                <span class="label">Unidade Operadora</span>
                                <span class="value" style="color: var(--accent-cyan)">${item.deployed_units}</span>
                            </div>
                        </div>

                        <p class="eq-description">${item.description}</p>

                        <div class="eq-sector-info">
                            <i class="fa-solid fa-location-dot"></i>
                            <span>Destacamento: <strong>${item.location_name}</strong></span>
                        </div>
                    </div>

                    <div class="eq-card-footer">
                        <a href="index.html?lat=${item.latitude}&lng=${item.longitude}&zoom=11" class="btn-map-fly">
                            <i class="fa-solid fa-crosshairs"></i> Ver Posição no Mapa Tático
                        </a>
                    </div>
                </div>
            `;
        });

        gridEl.innerHTML = html;
    }

    return {
        init
    };
})();
