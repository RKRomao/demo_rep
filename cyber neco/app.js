/**
 * app.js - Lógica de Navegação, Simulador Financeiro e Gráficos do Plano de Negócios VTuber
 * Otimizado para Tema Claro (Pink/Rose)
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- Inicialização de Variáveis Globais ---
  let charts = {};
  
  // --- Lógica de Navegação por Abas (SPA) ---
  const sidebarLinks = document.querySelectorAll('.sidebar-link');
  const tabContents = document.querySelectorAll('.tab-content');

  sidebarLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      
      // Remover classe active de todos os links
      sidebarLinks.forEach(item => item.classList.remove('active'));
      
      // Adicionar classe active ao link clicado
      link.classList.add('active');
      
      // Esconder todas as abas
      tabContents.forEach(tab => tab.classList.remove('active'));
      
      // Mostrar a aba correspondente
      const targetTabId = link.getAttribute('data-tab');
      const targetTab = document.getElementById(targetTabId);
      if (targetTab) {
        targetTab.classList.add('active');
        
        // Destruir e re-desenhar gráficos específicos para garantir que renderizam com o tamanho correto
        handleTabCharts(targetTabId);
      }
    });
  });

  // --- Função para tratar renderização de gráficos nas abas ---
  function handleTabCharts(tabId) {
    if (tabId === 'tab-investimento') {
      initInvestimentoChart();
    } else if (tabId === 'tab-custos-receitas') {
      initCustosReceitasChart();
      updateSimulator(); // Atualiza os displays do simulador
    } else if (tabId === 'tab-evolucao') {
      initEvolucaoChart('12m'); // Por defeito, inicia com 12 meses
      initBenchmarksChart();
    }
  }

  // --- 1. Gráfico de Investimento Inicial (Doughnut) ---
  function initInvestimentoChart() {
    const ctx = document.getElementById('chartInvestimento');
    if (!ctx) return;
    
    if (charts.investimento) {
      charts.investimento.destroy();
    }

    charts.investimento = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Avatar & Arte', 'Equipamento', 'Software', 'Marketing'],
        datasets: [{
          data: [1750, 2170, 15, 150], // Baseado nos dados reais exportados dos CSVs
          backgroundColor: ['#ff758f', '#ffb3c6', '#c8b6ff', '#c9ada7'],
          borderWidth: 3,
          borderColor: '#ffffff', // Borda branca separa as fatias de forma limpa no tema claro
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#2C1A24', // Cor escura para legibilidade no tema claro
              font: {
                family: 'Outfit',
                size: 13
              },
              padding: 20
            }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.raw || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = Math.round((value / total) * 100);
                return ` ${label}: ${value.toLocaleString('pt-PT')} € (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  }

  // --- 2. Gráfico de Custos vs Receitas Base (Barra Comparativa) ---
  function initCustosReceitasChart() {
    const ctx = document.getElementById('chartCustosReceitas');
    if (!ctx) return;

    if (charts.custosReceitas) {
      charts.custosReceitas.destroy();
    }

    charts.custosReceitas = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Custos (Normais)', 'Custos (Otimizados)', 'Receitas Base', 'Lucro Otimizado'],
        datasets: [{
          label: 'Valor Mensal (€)',
          data: [305, 170, 420, 250],
          backgroundColor: ['#e63946', '#f77f00', '#38b000', '#FFA8EF'],
          borderWidth: 0,
          borderRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return ` ${context.raw} €`;
              }
            }
          }
        },
        scales: {
          y: {
            grid: {
              color: '#EAD0D6' // Grelha clara rosada para tema claro
            },
            ticks: {
              color: '#7D5C6E',
              callback: function(value) {
                return value + ' €';
              }
            }
          },
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#2C1A24',
              font: {
                family: 'Outfit'
              }
            }
          }
        }
      }
    });
  }

  // --- 3. Gráficos de Evolução (Linha - 12 Meses vs 3 Anos) ---
  const btn12m = document.getElementById('btn-proj-12m');
  const btn36m = document.getElementById('btn-proj-36m');
  
  if (btn12m && btn36m) {
    btn12m.addEventListener('click', () => {
      btn12m.classList.add('active');
      btn36m.classList.remove('active');
      initEvolucaoChart('12m');
    });

    btn36m.addEventListener('click', () => {
      btn36m.classList.add('active');
      btn12m.classList.remove('active');
      initEvolucaoChart('36m');
    });
  }

  function initEvolucaoChart(mode) {
    const ctx = document.getElementById('chartEvolucao');
    if (!ctx) return;

    if (charts.evolucao) {
      charts.evolucao.destroy();
    }

    let labels, dataCCV, dataSubs, dataReceitas;

    if (mode === '12m') {
      // Projeção 1º Ano (12 Meses)
      labels = ['Mês 1', 'Mês 2', 'Mês 3', 'Mês 4 (Debut)', 'Mês 5', 'Mês 6', 'Mês 7', 'Mês 8', 'Mês 9', 'Mês 10', 'Mês 11', 'Mês 12 (Ano 1)'];
      dataCCV = [0, 0, 0, 15, 25, 40, 50, 65, 80, 90, 100, 110]; // Média de Viewers Simultâneos (CCV)
      dataSubs = [0, 0, 0, 20, 45, 80, 110, 140, 180, 210, 235, 250]; // Subs na Twitch
      dataReceitas = [0, 0, 0, 100, 180, 280, 360, 450, 550, 620, 700, 750]; // Receita Total (€)
    } else {
      // Projeção Longo Prazo (3 Anos - 36 Meses amostrados de 4 em 4 meses)
      labels = ['Mês 1', 'Mês 4 (Debut)', 'Mês 8', 'Mês 12 (Ano 1)', 'Mês 16', 'Mês 20', 'Mês 24 (Ano 2)', 'Mês 28', 'Mês 32', 'Mês 36 (Ano 3)'];
      dataCCV = [0, 15, 65, 110, 145, 185, 220, 270, 310, 350];
      dataSubs = [0, 20, 140, 250, 400, 550, 680, 800, 900, 1000];
      dataReceitas = [0, 100, 450, 750, 1200, 1600, 2100, 2600, 3200, 3800]; // Receita em expansão (Merch/Sponsors)
    }

    charts.evolucao = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Média de Espectadores (CCV)',
            data: dataCCV,
            borderColor: '#ff758f',
            backgroundColor: '#ff758f',
            borderWidth: 3,
            pointRadius: 4,
            tension: 0.15,
            yAxisID: 'y'
          },
          {
            label: 'Assinaturas (Subs)',
            data: dataSubs,
            borderColor: '#BDB2FF',
            backgroundColor: '#BDB2FF',
            borderWidth: 3,
            pointRadius: 4,
            tension: 0.15,
            yAxisID: 'y'
          },
          {
            label: 'Receita Mensal Estimada (€)',
            data: dataReceitas,
            borderColor: '#38b000',
            backgroundColor: '#38b000',
            borderWidth: 3,
            pointRadius: 4,
            tension: 0.15,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#2C1A24',
              font: {
                family: 'Outfit'
              }
            }
          }
        },
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            grid: {
              color: '#EAD0D6'
            },
            ticks: {
              color: '#7D5C6E'
            },
            title: {
              display: true,
              text: 'Audiência / Subs',
              color: '#2C1A24'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            grid: {
              drawOnChartArea: false // Evita grelhas cruzadas
            },
            ticks: {
              color: '#38b000',
              callback: function(value) {
                return value + ' €';
              }
            },
            title: {
              display: true,
              text: 'Rendimentos (€)',
              color: '#38b000'
            }
          },
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#2C1A24',
              font: {
                family: 'Outfit'
              }
            }
          }
        }
      }
    });
  }

  // --- 4. Gráfico de Benchmarks do Setor (Barras Verticais) ---
  function initBenchmarksChart() {
    const ctx = document.getElementById('chartBenchmarks');
    if (!ctx) return;

    if (charts.benchmarks) {
      charts.benchmarks.destroy();
    }

    charts.benchmarks = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Indie Iniciante', 'Indie Médio', 'Neko (Ano 1)', 'Neko (Ano 3)', 'Agência (Média)', 'Estrela do Setor'],
        datasets: [
          {
            label: 'Média Espectadores (CCV)',
            data: [8, 80, 110, 350, 1200, 6000],
            backgroundColor: '#ff758f',
            yAxisID: 'y'
          },
          {
            label: 'Rendimento Mensal (€)',
            data: [80, 650, 750, 3800, 8000, 45000],
            backgroundColor: '#BDB2FF',
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#2C1A24',
              font: {
                family: 'Outfit'
              }
            }
          }
        },
        scales: {
          y: {
            type: 'linear',
            position: 'left',
            grid: {
              color: '#EAD0D6'
            },
            ticks: {
              color: '#7D5C6E'
            },
            title: {
              display: true,
              text: 'Média Viewers (CCV)',
              color: '#ff758f'
            }
          },
          y1: {
            type: 'linear',
            position: 'right',
            grid: {
              drawOnChartArea: false
            },
            ticks: {
              color: '#7D5C6E',
              callback: function(value) {
                return value + ' €';
              }
            },
            title: {
              display: true,
              text: 'Receita Média (€/Mês)',
              color: '#BDB2FF'
            }
          },
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#2C1A24',
              font: {
                family: 'Outfit'
              }
            }
          }
        }
      }
    });
  }

  // --- 5. Lógica do Simulador Financeiro ---
  const inputSubs = document.getElementById('sim-subs');
  const inputDonations = document.getElementById('sim-donations');
  const inputPatreon = document.getElementById('sim-patreon');
  const inputAds = document.getElementById('sim-ads');
  const inputSponsors = document.getElementById('sim-sponsors');
  const chkOtimizado = document.getElementById('sim-otimizado');

  const displaySubsVal = document.getElementById('val-subs');
  const displayDonationsVal = document.getElementById('val-donations');
  const displayPatreonVal = document.getElementById('val-patreon');
  const displayAdsVal = document.getElementById('val-ads');
  const displaySponsorsVal = document.getElementById('val-sponsors');

  const displayReceitaMensal = document.getElementById('metric-receita-mensal');
  const displayCustosMensais = document.getElementById('metric-custos-mensais');
  const displayLucroMensal = document.getElementById('metric-lucro-mensal');
  const displayAcumuladoAno1 = document.getElementById('metric-ano1-total');
  const displayAcumuladoAno3 = document.getElementById('metric-ano3-total');

  function updateSimulator() {
    if (!inputSubs) return; // Proteção caso não estejamos na aba correta ainda

    // Ler inputs
    const subs = parseInt(inputSubs.value);
    const donations = parseInt(inputDonations.value);
    const patreon = parseInt(inputPatreon.value);
    const ads = parseInt(inputAds.value);
    const sponsors = parseInt(inputSponsors.value);
    const usarOtimizado = chkOtimizado.checked;

    // Atualizar displays de texto dos sliders
    displaySubsVal.textContent = `${subs} subs`;
    displayDonationsVal.textContent = `${donations} €`;
    displayPatreonVal.textContent = `${patreon} €`;
    displayAdsVal.textContent = `${ads} €`;
    displaySponsorsVal.textContent = `${sponsors} €`;

    // Fórmulas
    // Cada sub vale em média 50% de 5€ (sub base da Twitch em PT é aprox. 4€, mas o plano estima ~2.50€ por sub líquida)
    const receitaSubs = subs * 2.50;
    const totalReceita = receitaSubs + donations + patreon + ads + sponsors;
    
    // Custos: 170€ (otimizado) ou 305€ (normal)
    const totalCusto = usarOtimizado ? 170 : 305;
    
    const lucroMensal = totalReceita - totalCusto;
    
    // Investimento Inicial (para abater no saldo acumulado)
    const investimentoInicial = 4085;

    // Projeções acumuladas a 12 e 36 meses
    // Assumindo estabilidade nestes valores
    const totalAcumuladoAno1 = (lucroMensal * 12) - investimentoInicial;
    const totalAcumuladoAno3 = (lucroMensal * 36) - investimentoInicial;

    // Escrever resultados no ecrã com classes de cor se negativo/positivo
    displayReceitaMensal.textContent = `${totalReceita.toLocaleString('pt-PT')} €`;
    displayCustosMensais.textContent = `${totalCusto.toLocaleString('pt-PT')} €`;
    
    // Lucro Mensal
    displayLucroMensal.textContent = `${lucroMensal.toLocaleString('pt-PT')} €`;
    setMetricColor(displayLucroMensal, lucroMensal);

    // Acumulado Ano 1
    displayAcumuladoAno1.textContent = `${totalAcumuladoAno1.toLocaleString('pt-PT')} €`;
    setMetricColor(displayAcumuladoAno1, totalAcumuladoAno1);

    // Acumulado Ano 3
    displayAcumuladoAno3.textContent = `${totalAcumuladoAno3.toLocaleString('pt-PT')} €`;
    setMetricColor(displayAcumuladoAno3, totalAcumuladoAno3);
  }

  function setMetricColor(element, value) {
    if (value < 0) {
      element.style.color = 'var(--color-danger)';
    } else {
      element.style.color = 'var(--color-success)';
    }
  }

  // Adicionar Event Listeners aos controlos do simulador
  const simuladorInputs = [inputSubs, inputDonations, inputPatreon, inputAds, inputSponsors, chkOtimizado];
  simuladorInputs.forEach(input => {
    if (input) {
      input.addEventListener('input', updateSimulator);
      input.addEventListener('change', updateSimulator);
    }
  });

  // --- Inicialização Automática da Primeira Aba ---
  // A aba inicial é 'tab-site-oficial' (não tem gráficos)
  // Mas se for recarregado noutra aba, tratamos de atualizar os gráficos
  const activeTab = document.querySelector('.tab-content.active');
  if (activeTab) {
    handleTabCharts(activeTab.id);
  }
});
