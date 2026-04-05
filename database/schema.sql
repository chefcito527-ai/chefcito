CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT        NOT NULL UNIQUE,
  nombre        TEXT        NOT NULL,
  password_hash TEXT        NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

CREATE TABLE IF NOT EXISTS solicitudes (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ingredientes TEXT        NOT NULL,
  personas     INTEGER     NOT NULL DEFAULT 1 CHECK (personas >= 1 AND personas <= 50),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_solicitudes_user_id ON solicitudes (user_id);

CREATE TABLE IF NOT EXISTS recetas (
  id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  solicitud_id       UUID        NOT NULL REFERENCES solicitudes(id) ON DELETE CASCADE,
  user_id            UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  titulo_plato       TEXT        NOT NULL,
  lista_ingredientes JSONB       NOT NULL DEFAULT '[]',
  pasos_preparacion  JSONB       NOT NULL DEFAULT '[]',
  tiempo_estimado    TEXT,
  nivel_dificultad   TEXT        CHECK (nivel_dificultad IN ('Fácil', 'Medio', 'Difícil')),
  guardada           BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recetas_user_id      ON recetas (user_id);
CREATE INDEX IF NOT EXISTS idx_recetas_solicitud_id ON recetas (solicitud_id);
CREATE INDEX IF NOT EXISTS idx_recetas_guardada     ON recetas (user_id, guardada);