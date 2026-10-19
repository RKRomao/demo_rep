-- ============================================================================
-- WARZONE GIS DATABASE SCHEMA (MariaDB 10.5+ / MySQL 8.0+)
-- Spatial Reference System: WGS 84 (SRID 4326)
-- ============================================================================

CREATE DATABASE IF NOT EXISTS warzone_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE warzone_db;

-- ----------------------------------------------------------------------------
-- 1. CATEGORIAS DE UNIDADES & SIMBOLOGIA MILITAR (NATO APP-6D / MIL-STD-2525)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS unit_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,          -- ex: INFANTRY, ARTILLERY, ARMOR, AVIATION, DRONE_SSO, HQ
    name VARCHAR(100) NOT NULL,                 -- ex: Infantaria Mecanizada
    nato_symbol_code VARCHAR(30) NOT NULL,      -- Código SIDC NATO (ex: SFGPU------)
    icon_svg TEXT,                              -- Ícone visual SVG fallback
    default_faction ENUM('BLUFOR', 'OPFOR', 'NEUTRAL') NOT NULL DEFAULT 'BLUFOR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 2. DESTACAMENTOS & UNIDADES MILITARES NO TERRENO
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS units (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,                 -- ex: 47ª Brigada Mecanizada "Magura"
    category_id INT NOT NULL,
    faction ENUM('BLUFOR', 'OPFOR', 'NEUTRAL') NOT NULL DEFAULT 'BLUFOR',
    echelon ENUM('SECTION', 'PLATOON', 'COMPANY', 'BATALLION', 'BRIGADE', 'DIVISION', 'CORPS') NOT NULL DEFAULT 'BRIGADE',
    commander VARCHAR(150),                     -- Nome do Comandante
    equipment_summary TEXT,                     -- ex: M2A2 Bradley, Leopard 2A6, HIMARS
    personnel_count INT DEFAULT 0,
    status ENUM('ACTIVE', 'ENGAGED', 'RESERVE', 'RETREATED', 'DESTROYED') DEFAULT 'ACTIVE',
    location POINT NOT NULL,          -- Coordenadas WGS84 (Longitude, Latitude)
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES unit_categories(id) ON DELETE CASCADE,
    SPATIAL INDEX(location)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 3. ZONAS DE CONTROLO TERRITORIAL E LINHAS DA FRENTE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS territorial_zones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,                 -- ex: Donbas Ocupado, Saliente de Kursk
    zone_type ENUM('SOVEREIGN', 'OCCUPIED', 'LIBERATED', 'ACTIVE_CONFLICT', 'INCURSION') NOT NULL,
    valid_from DATE NOT NULL,                   -- Suporte à Máquina do Tempo
    valid_to DATE DEFAULT NULL,                 -- NULL indica atualidade (2026)
    boundary GEOMETRY NOT NULL,       -- Polígono WGS84
    fill_color VARCHAR(10) DEFAULT '#FF0000',
    stroke_color VARCHAR(10) DEFAULT '#880000',
    fill_opacity FLOAT DEFAULT 0.35,
    area_sq_km DECIMAL(10,2) DEFAULT 0.00,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    SPATIAL INDEX(boundary)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 4. EVENTOS E ACONTECIMENTOS OSINT
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS osint_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,          -- ex: LiveUAmap, Telegram, ISW, NASA FIRMS
    external_id VARCHAR(255),                  -- Hash para desduplicação
    category ENUM('SHELLING', 'TROOP_MOVEMENT', 'AIRSTRIKE', 'DRONE_ATTACK', 'TERRITORY_CHANGE', 'INFRASTRUCTURE', 'NAVAL_OPS') NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_timestamp DATETIME NOT NULL,
    location POINT NOT NULL,          -- Coordenadas WGS84
    reliability_score TINYINT DEFAULT 4,        -- Confiança (1 a 5)
    verified BOOLEAN DEFAULT TRUE,
    raw_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY idx_source_ext (source_name, external_id),
    SPATIAL INDEX(location)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 5. FERRAMENTAS TÁTICAS E DESENHOS DO UTILIZADOR (QUADRO TÁTICO)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tactical_drawings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_session_id VARCHAR(100) NOT NULL DEFAULT 'default_session',
    title VARCHAR(150),
    drawing_type ENUM('ADVANCE_ARROW', 'DEFENSIVE_POLY', 'FLANKING_LINE', 'MEASUREMENT', 'NOTE_MARKER') NOT NULL,
    geometry GEOMETRY NOT NULL,       -- Point, LineString, ou Polygon
    style_properties JSON NOT NULL,             -- Cor, espessura, opacidade, dashArray
    tactical_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    SPATIAL INDEX(geometry)
) ENGINE=InnoDB;

-- ============================================================================
-- DADOS DE INICIALIZAÇÃO E TESTE (SEED DATA)
-- ============================================================================

-- Categorias NATO APP-6D
INSERT INTO unit_categories (code, name, nato_symbol_code, default_faction) VALUES
('INFANTRY', 'Infantaria Mecanizada', 'SFGPUCI----D---', 'BLUFOR'),
('ARMOR', 'Cavalaria Blindada', 'SFGPUCA----D---', 'BLUFOR'),
('ARTILLERY', 'Artilharia / Rocket System', 'SFGPUCA---FA---', 'BLUFOR'),
('AVIATION', 'Aviação de Caça / Helicópteros', 'SFGPUAV----D---', 'BLUFOR'),
('DRONE_SSO', 'Drones FPV & Forças Especiais (SSO)', 'SFGPUCR----D---', 'BLUFOR'),
('HQ', 'Quartel-General Tático (TCP)', 'SFGPUHQ----D---', 'BLUFOR'),
('OPFOR_INF', 'Infantaria Inimiga', 'SHGPUCI----D---', 'OPFOR'),
('OPFOR_ARMOR', 'Cavalaria Blindada Inimiga', 'SHGPUCA----D---', 'OPFOR'),
('OPFOR_HQ', 'Posto de Comando Inimigo', 'SHGPUHQ----D---', 'OPFOR')
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- Unidades Exemplo (Coordenadas WGS84: Longitude Latitude)
INSERT INTO units (name, category_id, faction, echelon, commander, equipment_summary, personnel_count, status, location) VALUES
('47ª Brigada Mecanizada "Magura"', 1, 'BLUFOR', 'BRIGADE', 'Cel. Pavlo Palisa', 'M2A2 Bradley, Leopard 2A6, M113', 3500, 'ENGAGED', ST_GeomFromText('POINT(37.1824 48.2820)')),
('82ª Brigada de Assalto Aéreo', 1, 'BLUFOR', 'BRIGADE', 'Ten.-Cel. Yevhen Moisiuk', 'Stryker, Marder 1A3, Challenger 2', 2800, 'ACTIVE', ST_GeomFromText('POINT(35.3200 51.1500)')),
('Unidade de Drones "Madyar Birds"', 5, 'BLUFOR', 'COMPANY', 'Cap. Robert "Madyar" Brovdi', 'Drones FPV Kamikaze, Heavy Bomber Drones', 450, 'ENGAGED', ST_GeomFromText('POINT(37.8000 48.4000)')),
('Posto de Comando Operacional Sul (BLUFOR HQ)', 6, 'BLUFOR', 'CORPS', 'Gen. Oleksandr Syrskyi', 'Sistemas C4ISR, Comunicações Starlink', 800, 'ACTIVE', ST_GeomFromText('POINT(35.1396 47.8388)')),
('1ª Brigada de Infantaria de Guardas (OPFOR)', 7, 'OPFOR', 'BRIGADE', 'Gen.-Maj. V. Gerasimov', 'T-90M Proryv, BMP-3, BTR-82A', 4200, 'ENGAGED', ST_GeomFromText('POINT(37.5000 48.2000)')),
('Posto de Comando OPFOR "Surovikin"', 9, 'OPFOR', 'DIVISION', 'Gen. Surovikin', 'Sistemas EW Krasukha-4, S-400', 1200, 'ACTIVE', ST_GeomFromText('POINT(38.2000 47.5000)'))
ON DUPLICATE KEY UPDATE status=VALUES(status);

-- Zonas de Controlo Territorial (WGS84 Polygon Coordinates: LONGITUDE LATITUDE)
INSERT INTO territorial_zones (name, zone_type, valid_from, valid_to, boundary, fill_color, stroke_color, fill_opacity, area_sq_km, notes) VALUES
(
    'Península da Crimeia (Ocupada)', 
    'OCCUPIED', 
    '2022-02-24', 
    NULL, 
    ST_GeomFromText('POLYGON((33.60 46.15, 33.85 46.00, 34.30 45.95, 34.70 46.00, 35.05 45.85, 35.35 45.65, 36.10 45.40, 36.45 45.35, 36.65 45.22, 36.45 45.05, 36.20 45.00, 35.80 45.05, 34.90 44.75, 34.40 44.50, 34.10 44.40, 33.70 44.45, 33.50 44.55, 33.40 44.65, 33.55 44.90, 33.25 45.10, 32.65 45.35, 32.48 45.70, 32.80 45.82, 33.20 45.68, 33.40 45.88, 33.60 46.15))'),
    '#EF4444', 
    '#991B1B', 
    0.35, 
    27000.00, 
    'Área ocupada desde 2014, linha costeira fortificada.'
),
(
    'Donbas & Corredor de Azov (Ocupado)', 
    'OCCUPIED', 
    '2022-02-24', 
    NULL, 
    ST_GeomFromText('POLYGON((37.10 49.50, 37.60 49.85, 38.20 49.90, 38.80 49.75, 39.50 49.80, 40.10 49.45, 40.25 49.10, 39.90 48.65, 40.05 48.20, 39.85 47.70, 39.20 47.15, 38.80 47.10, 38.25 47.10, 37.90 46.90, 37.50 47.10, 37.20 46.90, 36.80 46.75, 36.40 46.85, 36.10 46.65, 36.60 47.10, 37.10 47.35, 37.55 47.75, 37.80 48.00, 37.60 48.40, 37.95 48.65, 37.70 48.95, 37.20 49.10, 37.10 49.50))'),
    '#DC2626', 
    '#7F1D1D', 
    0.35, 
    34500.00, 
    'Setor Leste do Donbas e faixa costeira de Azov.'
),
(
    'Linha de Conflito Ativo (Faixa Tática 1200km)', 
    'ACTIVE_CONFLICT', 
    '2024-01-01', 
    NULL, 
    ST_GeomFromText('POLYGON((37.10 49.80, 37.45 49.60, 37.90 49.30, 38.15 49.00, 37.90 48.70, 37.70 48.40, 37.60 48.10, 37.30 47.90, 37.10 47.70, 36.60 47.45, 36.20 47.40, 35.70 47.45, 35.35 47.60, 35.15 47.45, 34.70 47.25, 33.80 47.00, 33.40 46.82, 33.00 46.70, 32.55 46.65, 32.40 46.75, 32.80 46.85, 33.30 47.00, 33.90 47.25, 34.50 47.40, 34.90 47.55, 35.40 47.75, 35.90 47.65, 36.40 47.60, 36.90 47.90, 37.20 48.20, 37.40 48.50, 37.30 48.80, 37.50 49.10, 37.20 49.40, 36.90 49.70, 37.10 49.80))'),
    '#F59E0B', 
    '#B45309', 
    0.40, 
    12000.00, 
    'Corredor de confronto direto de artilharia e infantaria.'
),
(
    'Incursão Tática em Kursk (Saliente)', 
    'INCURSION', 
    '2024-08-06', 
    NULL, 
    ST_GeomFromText('POLYGON((35.00 51.35, 35.15 51.42, 35.30 51.45, 35.45 51.40, 35.58 51.30, 35.65 51.20, 35.60 51.10, 35.48 51.02, 35.32 50.98, 35.18 51.03, 35.05 51.12, 34.95 51.22, 35.00 51.35))'),
    '#06B6D4', 
    '#0E7490', 
    0.40, 
    1350.00, 
    'Saliente tático em Sudzha sob controlo das forças armadas.'
),
(
    'Zaporizhzhia & Margem Esquerda de Kherson',
    'OCCUPIED',
    '2022-02-24',
    NULL,
    ST_GeomFromText('POLYGON((34.80 46.75, 35.20 46.85, 35.70 46.90, 36.10 46.65, 36.40 46.85, 36.80 46.75, 35.90 46.30, 35.30 46.20, 34.70 46.05, 34.00 46.10, 33.70 46.15, 33.10 46.25, 32.60 46.40, 32.30 46.55, 32.55 46.65, 33.00 46.70, 33.40 46.82, 33.80 47.00, 34.30 47.15, 34.70 47.25, 35.10 47.45, 35.35 47.60, 35.10 47.30, 34.80 46.75))'),
    '#EF4444',
    '#991B1B',
    0.35,
    26000.00,
    'Corredor terrestre do sul acompanhando o curso do Rio Dnieper e Central Nuclear de Zaporizhzhia.'
),
(
    'Territórios Libertados (Kharkiv & Kherson Ocidental)',
    'LIBERATED',
    '2022-09-01',
    NULL,
    ST_GeomFromText('POLYGON((36.10 49.80, 36.60 50.10, 37.10 49.80, 36.90 49.70, 37.20 49.40, 36.80 49.10, 36.10 49.20, 35.60 49.40, 36.10 49.80))'),
    '#10B981',
    '#047857',
    0.25,
    18400.00,
    'Zonas libertadas com sucesso durante a contra-ofensiva de Kharkiv e margem direita de Kherson.'
),
(
    'Ucrânia Livre Soberana (Centro, Norte e Oeste)',
    'SOVEREIGN',
    '1991-08-24',
    NULL,
    ST_GeomFromText('POLYGON((24.00 51.50, 28.50 51.80, 33.00 52.30, 35.00 51.12, 34.70 49.80, 33.90 47.25, 32.40 46.75, 30.50 46.20, 29.50 45.30, 28.60 45.40, 24.20 48.00, 22.20 48.50, 24.00 51.50))'),
    '#0057B7',
    '#FFD700',
    0.20,
    430000.00,
    'Território soberano sob controlo legítimo das Forças Armadas e Governo da Ucrânia (Kyiv, Lviv, Odesa).'
),
(
    'Fronteira Defensiva do Norte (Chernihiv, Sumy & Kyiv Norte)',
    'LIBERATED',
    '2022-04-01',
    NULL,
    ST_GeomFromText('POLYGON((29.50 51.50, 31.20 52.10, 33.50 52.40, 35.20 51.50, 34.50 50.80, 32.80 50.90, 30.50 51.10, 29.50 51.50))'),
    '#10B981',
    '#047857',
    0.25,
    52000.00,
    'Região norte libertada em Abril de 2022 após a Batalha de Kyiv.'
),
(
    'Setor de Conflito Transfronteiriço (Belgorod & Bryansk)',
    'ACTIVE_CONFLICT',
    '2023-01-01',
    NULL,
    ST_GeomFromText('POLYGON((35.50 50.90, 36.80 50.60, 37.50 50.30, 38.20 50.10, 37.80 49.90, 36.50 50.20, 35.20 50.60, 35.50 50.90))'),
    '#F59E0B',
    '#B45309',
    0.35,
    9800.00,
    'Zona de escaramuças de artilharia, ataques de drones e incursões transfronteiriças.'
);

-- Eventos OSINT Iniciais
INSERT INTO osint_events (source_name, external_id, category, title, description, event_timestamp, location, reliability_score, verified) VALUES
('LiveUAmap', 'evt_1001', 'DRONE_ATTACK', 'Ataque de Drones Shahed em Kyiv', 'Defesa aérea abateu múltiplos drones sobrevoando a região metropolitana.', NOW() - INTERVAL 2 HOUR, ST_GeomFromText('POINT(30.5234 50.4501)'), 5, TRUE),
('ISW', 'evt_1002', 'TROOP_MOVEMENT', 'Avance Tático no Sector de Pokrovsk', 'Formações blindadas registaram movimentação ao redor da autoestrada T0504.', NOW() - INTERVAL 5 HOUR, ST_GeomFromText('POINT(37.1824 48.2820)'), 4, TRUE),
('NASA_FIRMS', 'evt_1003', 'SHELLING', 'Anomalias Térmicas Detectadas em Chasiv Yar', 'Incêndios provocados por duelo de artilharia pesada detectados por satélite.', NOW() - INTERVAL 1 HOUR, ST_GeomFromText('POINT(37.8333 48.5833)'), 5, TRUE);
