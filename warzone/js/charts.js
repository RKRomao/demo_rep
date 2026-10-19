/**
 * WARZONE CHARTS MODULE
 * Módulo para inicialização e atualização de gráficos analíticos com Chart.js.
 */

const WarzoneCharts = (function () {
    let categoryChart = null;

    /**
     * Inicializar Gráficos
     */
    function initCharts(eventsData = []) {
        const ctx = document.getElementById('categoryChart');
        if (!ctx) return;

        // Calcular estatísticas por categoria
        const categoryCounts = {
            missile_strike: 0,
            drone_attack: 0,
            ground_combat: 0,
            air_defense: 0,
            naval_ops: 0,
            infrastructure: 0
        };

        eventsData.forEach(e => {
            if (categoryCounts[e.category] !== undefined) {
                categoryCounts[e.category]++;
            }
        });

        // Se dados zerados, colocar contagens demonstrativas
        if (Object.values(categoryCounts).every(v => v === 0)) {
            categoryCounts.missile_strike = 45;
            categoryCounts.drone_attack = 82;
            categoryCounts.ground_combat = 110;
            categoryCounts.air_defense = 64;
            categoryCounts.naval_ops = 18;
            categoryCounts.infrastructure = 35;
        }

        categoryChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Mísseis', 'Drones', 'Combate Terrestre', 'Defesa Aérea', 'Naval', 'Energia'],
                datasets: [{
                    data: [
                        categoryCounts.missile_strike,
                        categoryCounts.drone_attack,
                        categoryCounts.ground_combat,
                        categoryCounts.air_defense,
                        categoryCounts.naval_ops,
                        categoryCounts.infrastructure
                    ],
                    backgroundColor: [
                        '#FF334B',
                        '#FF9900',
                        '#DC2626',
                        '#00F0FF',
                        '#0057B7',
                        '#10B981'
                    ],
                    borderWidth: 1,
                    borderColor: '#0B0F19'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#9CA3AF',
                            font: {
                                family: 'JetBrains Mono',
                                size: 10
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Atualizar dados do gráfico
     */
    function updateCharts(eventsData = []) {
        if (!categoryChart) return;
        const categoryCounts = {
            missile_strike: 0,
            drone_attack: 0,
            ground_combat: 0,
            air_defense: 0,
            naval_ops: 0,
            infrastructure: 0
        };

        eventsData.forEach(e => {
            if (categoryCounts[e.category] !== undefined) {
                categoryCounts[e.category]++;
            }
        });

        categoryChart.data.datasets[0].data = Object.values(categoryCounts);
        categoryChart.update();
    }

    return {
        initCharts,
        updateCharts
    };
})();
