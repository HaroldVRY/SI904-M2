-- =====================================================
-- SecureVision AI -- Base de datos Supabase/PostgreSQL
-- SI904-M2 -- Universidad Nacional de Ingenieria
-- =====================================================

-- Sesiones de monitoreo
CREATE TABLE sesiones (
  id                BIGSERIAL PRIMARY KEY,
  inicio            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  fin               TIMESTAMPTZ,
  total_frames      INTEGER      DEFAULT 0,
  total_alertas     INTEGER      DEFAULT 0,
  modelos_activos   TEXT[]       NOT NULL DEFAULT '{armas,rostros}',
  fuente_video      TEXT         DEFAULT '0',
  conf_threshold    NUMERIC(4,2) DEFAULT 0.40
);

-- Detecciones individuales (una fila por objeto detectado)
CREATE TABLE detecciones (
  id              BIGSERIAL PRIMARY KEY,
  sesion_id       BIGINT       REFERENCES sesiones(id) ON DELETE CASCADE,
  detectado_en    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  tipo            TEXT         NOT NULL CHECK (tipo IN ('armas','rostros','placas')),
  clase           TEXT         NOT NULL,
  confianza       NUMERIC(5,4) NOT NULL,
  x1 INTEGER, y1 INTEGER,
  x2 INTEGER, y2 INTEGER,
  disparo_alerta  BOOLEAN      DEFAULT FALSE
);

-- Alertas enviadas por WhatsApp
CREATE TABLE alertas_whatsapp (
  id               BIGSERIAL PRIMARY KEY,
  sesion_id        BIGINT       REFERENCES sesiones(id) ON DELETE CASCADE,
  enviada_en       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  numero_destino   TEXT         NOT NULL,
  estado           TEXT         DEFAULT 'enviada'
                                CHECK (estado IN ('enviada','entregada','fallida')),
  twilio_sid       TEXT,
  mensaje_texto    TEXT,
  detecciones_json JSONB
);

-- Indices de rendimiento
CREATE INDEX idx_det_sesion ON detecciones(sesion_id);
CREATE INDEX idx_det_tipo   ON detecciones(tipo);
CREATE INDEX idx_det_ts     ON detecciones(detectado_en DESC);
CREATE INDEX idx_alerta_ses ON alertas_whatsapp(sesion_id);

-- Vista de resumen para el dashboard
CREATE VIEW v_resumen_sesiones AS
SELECT
  s.id, s.inicio, s.fin, s.total_frames, s.total_alertas,
  COUNT(d.id)                                        AS total_detecciones,
  COUNT(d.id) FILTER (WHERE d.tipo = 'armas')        AS det_armas,
  COUNT(d.id) FILTER (WHERE d.tipo = 'rostros')      AS det_rostros,
  COUNT(d.id) FILTER (WHERE d.tipo = 'placas')       AS det_placas
FROM sesiones s
LEFT JOIN detecciones d ON d.sesion_id = s.id
GROUP BY s.id;
