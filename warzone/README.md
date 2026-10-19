# 🪖 WARZONE - Ukraine-Russia Conflict Tracker & Tactical Map

> **Plataforma de Monitorização Tática em Tempo Real, Análise Geospacial OSINT e Simbologia Militar NATO APP-6D / MIL-STD-2525**

![WARZONE Banner](https://img.shields.io/badge/WARZONE-Conflict%20Tracker-red?style=for-the-badge&logo=shield)
![Node.js](https://img.shields.io/badge/Backend-Node.js%20%7C%20Express-green?style=for-the-badge&logo=nodedotjs)
![MariaDB](https://img.shields.io/badge/Database-MariaDB-blue?style=for-the-badge&logo=mariadb)
![Leaflet](https://img.shields.io/badge/Map-Leaflet%20%7C%20OpenStreetMap-1976D2?style=for-the-badge&logo=openstreetmap)

---

## 📌 Visão Geral

O **WARZONE Tracker** é uma aplicação web de inteligência geográfica e acompanhamento militar concebida para mapear, analisar e visualizar a evolução do conflito entre a Ucrânia e a Rússia desde **Fevereiro de 2022 até 2026**. 

A plataforma combina dados validados do **Institute for the Study of War (ISW)**, telemetria de satélite **NASA FIRMS**, feeds **LiveUAmap** e redes **OSINT** com uma interface cartográfica interativa baseada em **OpenStreetMap**.

---

## 🚀 Principais Funcionalidades

### 1. ⏳ Máquina do Tempo Histórica (2022 - 2026)
- **Metamorfose Poligonal de Controlo Territorial (`getHistoricalZones`)**: O slider temporal no rodapé permite viajar no tempo entre 5 eras operacionais distintas:
  - ⏪ **Fev / Mar 2022**: Invasão Inicial Total do Norte, cerco a Kyiv, Kharkiv e Kherson.
  - ⏪ **Mid 2022**: Batalha do Donbas (Severodonetsk/Lysychansk) e concentração no Sul.
  - ⏪ **Set / Out 2022**: Contra-ofensiva relâmpago de Kharkiv e libertação de Izyum/Kupyansk.
  - ⏪ **Nov 2022 - 2023**: Libertação da Cidade de Kherson (Margem Direita) e Batalha de Bakhmut / Linha Surovikin (Robotyne).
  - ⏩ **2024 - 2026**: Atualidade, Pokrovsk, Chasiv Yar e Incursão Tática em Kursk (Rússia).
- **Cobertura Territorial 100% Completa**: Inclui permanentemente a zona soberana da Ucrânia (Azul), áreas ocupadas (Vermelho), libertadas (Verde), corredor de confronto direto de 1.200 km (Âmbar) e incursões (Ciano).

### 2. 🛡️ Simbologia Militar NATO APP-6D / MIL-STD-2525
- **BLUFOR (Azul)**: Marcadores retangulares de forças amigas por escalão (`I`, `II`, `III`) e ramo tático.
- **OPFOR (Vermelho)**: Losangos de formações inimigas.
- **Postos de Comando Tático (TCP)**: Marcadores de Quartel-General (`TCP ALPHA HQ` e `OPFOR HQ`).
- **Eixos de Ataque (AXIS SABRE / AXIS SUROVIKIN BREACH)**: Vetores de avanço e assalto blindado.
- **Linhas de Fase & Coordenação (PL ALPHA / FSCL / LOA)**: Linhas limite de avanço e apoio de fogo.
- **Objetivos Táticos (OBJ)**: Círculos e nós táticos identificados (`OBJ POKROVSK`, `OBJ ROBOTYNE`, `OBJ SUDZHA`).

### 3. 🪖 Unidades & Brigadas Militares Destacadas
- Aba dedicada na gaveta tática com **brasões oficiais, comandante, equipamento pesado** (M2A2 Bradley, Leopard 2A6, HIMARS, Drones FPV Madyar) e localização no mapa.
- Filtros por ramo militar: **Artilharia**, **Infantaria**, **Cavalaria Blindada** e **Drones / SSO**.

### 4. 🤖 Robô Autónomo de Web Scraping OSINT (5 em 5 Minutos)
- Varredura automática em segundo plano das fontes **NASA FIRMS**, **LiveUAmap**, **ISW**, **DeepState** e canais OSINT do **Telegram**.
- **Catálogo Topográfico de Locais Reais**: Ingestão associada a nós topográficos reais e verificados (Pokrovsk, Chasiv Yar, Kherson, Kharkiv, Dnipro, Sudzha, Kupyansk).
- **Filtro de Desduplicação Inteligente**: Impede entradas duplicadas na base de dados.
- Temporizador decrescente (`05:00`) no cabeçalho e botão de varredura instantânea (`/api/sync`).

### 5. 🖌️ Ferramentas de Desenho Tático Temporário (Leaflet Geoman)
- Desenho livre de polígonos, eixos de ataque, círculos de raio de alcance e marcadores sobre o OpenStreetMap.
- Os desenhos são **não-permanentes** (não alteram a MariaDB) e podem ser exportados para **GeoJSON**.

### 6. 📊 Gráficos & Estatísticas Táticas (Chart.js)
- Distribuição de acontecimentos por categoria e severidade.
- Taxa de interceção antiaérea, km² libertados e extensão da linha da frente (1.200 km).

---

## 🛠️ Arquitetura e Tecnologias

- **Frontend**: HTML5, CSS3 Vanilla (Glassmorphism & Neon Design), JavaScript ES6+ Modular.
- **Map Engine**: [Leaflet.js](https://leafletjs.com/) + OpenStreetMap Tiles + [Leaflet Geoman](https://geoman.io/) (Drawing Tools).
- **Charts Engine**: [Chart.js](https://www.chartjs.org/).
- **Backend API**: Node.js + Express.js REST API.
- **Base de Dados**: MariaDB (com motor automático *In-Memory Fallback*).

---

## 💻 Instalação e Execução

### Pré-requisitos
- **Node.js** (versão 16+)
- **npm**
- **MariaDB** *(opcional - a aplicação ativa o fallback em memória se a MariaDB não estiver a correr localmente)*

### Passos de Instalação

1. **Clonar o repositório**:
   ```bash
   git clone https://github.com/RKRomao/demo_rep.git
   cd demo_rep/warzone
   ```

2. **Instalar as dependências**:
   ```bash
   npm install
   ```

3. **Configurar as Variáveis de Ambiente (Opcional - `.env`)**:
   ```env
   PORT=3000
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=sua_senha
   DB_NAME=warzone_db
   ```

4. **Iniciar o Servidor Backend**:
   ```bash
   npm start
   # ou
   node server.js
   ```

5. **Abrir a Aplicação no Navegador**:
   ```text
   http://localhost:3000
   ```

---

## 📡 Endpoints da API REST (`server.js`)

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/api/status` | Verifica o estado do servidor e conexão à MariaDB |
| `GET` | `/api/zones` | Retorna as zonas de controlo territorial em formato GeoJSON |
| `GET` | `/api/events` | Retorna acontecimentos táticos (suporta filtros `category`, `severity`, `search`) |
| `GET` | `/api/units` | Retorna as brigadas e unidades militares destacadas (filtro `branch`) |
| `GET` | `/api/stats` | Retorna estatísticas globais do conflito |
| `POST` | `/api/events` | Regista um novo evento tático na base de dados |
| `POST` / `GET` | `/api/sync` | Força a execução imediata do robô de Web Scraping OSINT |

---

## 🗄️ Esquema da Base de Dados (MariaDB DDL)

Se desejar criar manualmente as tabelas na MariaDB:

```sql
CREATE DATABASE IF NOT EXISTS warzone_db;
USE warzone_db;

-- Tabela de Eventos de Conflito
CREATE TABLE IF NOT EXISTS conflict_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category ENUM('missile_strike', 'drone_attack', 'ground_combat', 'air_defense', 'naval_ops', 'infrastructure') DEFAULT 'ground_combat',
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    event_date DATE NOT NULL,
    location_name VARCHAR(150),
    description TEXT,
    source_url VARCHAR(500),
    verification_status ENUM('unconfirmed', 'verified', 'official_report') DEFAULT 'unconfirmed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Zonas de Controlo
CREATE TABLE IF NOT EXISTS conflict_zones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    control_status ENUM('ukraine', 'russia', 'contested', 'ukraine_liberated', 'ukraine_incursion') NOT NULL,
    geojson_polygon JSON NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## 📜 Licença e Créditos

- **Licença**: MIT License.
- **Fontes OSINT**: Institute for the Study of War (ISW), NASA FIRMS, LiveUAmap, DeepStateMap.
- **Simbologia**: Padrão MIL-STD-2525D / NATO APP-6D.
