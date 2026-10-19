/**
 * WARZONE TIMELINE MODULE
 * Controlador da Linha do Tempo (Time Machine) para navegação temporal nos eventos do conflito.
 */

const WarzoneTimeline = (function () {
    let isPlaying = false;
    let playInterval = null;
    let sliderEl = null;
    let dateDisplayEl = null;
    let playBtnEl = null;

    const YEAR_LABELS = {
        2022.0: 'FEVEREIRO 2022 (Fase Inicial da Invasão)',
        2022.5: 'JULHO 2022 (Batalha do Donbas Inicial)',
        2023.0: 'JANEIRO 2023 (Batalha de Bakhmut)',
        2023.5: 'JUNHO 2023 (Contra-Ofensiva do Sul)',
        2024.0: 'JANEIRO 2024 (Guerra de Atrito & Drones)',
        2025.0: 'JANEIRO 2025 (Linhas Defensivas Avançadas)',
        2026.0: 'JANEIRO 2026 (Operações Transfronteiriças)',
        2026.7: 'SETEMBRO 2026 (Presente)'
    };

    /**
     * Inicializar o Controlador da Linha do Tempo
     */
    function init() {
        sliderEl = document.getElementById('timelineSlider');
        dateDisplayEl = document.getElementById('currentTimelineDate');
        playBtnEl = document.getElementById('timelinePlayBtn');

        if (!sliderEl || !dateDisplayEl) return;

        sliderEl.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            updateTimelineView(val);
        });

        sliderEl.addEventListener('change', (e) => {
            const val = parseFloat(e.target.value);
            updateTimelineView(val);
        });

        if (playBtnEl) {
            playBtnEl.addEventListener('click', togglePlay);
        }
    }

    /**
     * Alternar reprodução automática da linha do tempo
     */
    function togglePlay() {
        isPlaying = !isPlaying;
        if (playBtnEl) {
            playBtnEl.innerHTML = isPlaying ? '<i class="fa-solid fa-pause"></i>' : '<i class="fa-solid fa-play"></i>';
        }

        if (isPlaying) {
            playInterval = setInterval(() => {
                let currentVal = parseFloat(sliderEl.value);
                currentVal += 0.1;
                if (currentVal > 2026.7) {
                    currentVal = 2022;
                }
                sliderEl.value = currentVal;
                updateTimelineView(currentVal);
            }, 1000);
        } else {
            clearInterval(playInterval);
        }
    }

    /**
     * Atualizar visualização do mapa e filtro de datas com base na posição do slider
     */
    function updateTimelineView(val) {
        // Encontrar legenda de data mais próxima
        let displayLabel = 'SETEMBRO 2026';
        if (val < 2022.5) displayLabel = 'FEVEREIRO 2022 (Fase Inicial da Invasão)';
        else if (val < 2023.0) displayLabel = 'SETEMBRO 2022 (Libertação de Kharkiv)';
        else if (val < 2023.5) displayLabel = 'JANEIRO 2023 (Batalha de Bakhmut)';
        else if (val < 2024.0) displayLabel = 'JULHO 2023 (Contra-ofensiva Zaporizhzhia)';
        else if (val < 2025.0) displayLabel = 'ANO 2024 (Atrito de Artilharia e Drones)';
        else if (val < 2026.0) displayLabel = 'ANO 2025 (Frente Estabilizada & Kursk)';
        else displayLabel = 'SETEMBRO 2026 (Presente)';

        if (dateDisplayEl) {
            dateDisplayEl.textContent = displayLabel;
        }

        // Notificar o App principal para atualizar os marcadores de eventos
        if (window.WarzoneApp && WarzoneApp.onTimelineChange) {
            WarzoneApp.onTimelineChange(val);
        }
    }

    /**
     * Definir data da linha do tempo programaticamente
     */
    function setTimelineDate(val) {
        if (!sliderEl) sliderEl = document.getElementById('timelineSlider');
        if (sliderEl) {
            sliderEl.value = val;
            updateTimelineView(val);
        }
    }

    return {
        init,
        updateTimelineView,
        setTimelineDate
    };
})();
