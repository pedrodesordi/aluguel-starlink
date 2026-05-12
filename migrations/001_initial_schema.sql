-- =============================================================
-- Schema: Sistema de Aluguel Starlink
-- =============================================================

-- Extensão para gerar bytes aleatórios (token do termo)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =============================================================
-- TABELA: usuarios
-- =============================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    senha_hash    TEXT NOT NULL,
    perfil        TEXT NOT NULL DEFAULT 'operador'
                      CHECK (perfil IN ('admin','operador')),
    ativo         BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
-- TABELA: clientes
-- =============================================================
CREATE TABLE IF NOT EXISTS clientes (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome          TEXT NOT NULL,
    cpf           VARCHAR(14) NOT NULL UNIQUE,
    telefone      VARCHAR(20),
    email         TEXT,
    endereco      TEXT,
    cidade        TEXT,
    estado        CHAR(2),
    observacoes   TEXT,
    ativo         BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
-- TABELA: equipamentos
-- =============================================================
CREATE TABLE IF NOT EXISTS equipamentos (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero_serie           TEXT NOT NULL UNIQUE,
    numero_starlink        TEXT UNIQUE,
    modelo                 TEXT NOT NULL,
    tipo_plano             TEXT,
    vencimento_mensalidade DATE,
    status                 TEXT NOT NULL DEFAULT 'disponivel'
                               CHECK (status IN ('disponivel','alugado','manutencao','baixado')),
    descricao              TEXT,
    data_aquisicao         DATE,
    valor_aquisicao        NUMERIC(10,2),
    criado_em              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
-- TABELA: faixas_preco_diaria
-- =============================================================
CREATE TABLE IF NOT EXISTS faixas_preco_diaria (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dias_min      INTEGER NOT NULL,
    dias_max      INTEGER NOT NULL,
    valor_por_dia NUMERIC(10,2) NOT NULL,
    ativo         BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_faixa CHECK (dias_min <= dias_max),
    CONSTRAINT chk_positivos CHECK (dias_min > 0 AND valor_por_dia > 0)
);

INSERT INTO faixas_preco_diaria (dias_min, dias_max, valor_por_dia) VALUES
    (1,  3,  80.00),
    (4,  7,  70.00),
    (8,  14, 60.00),
    (15, 30, 50.00)
ON CONFLICT DO NOTHING;

-- =============================================================
-- TABELA: alugueis
-- =============================================================
CREATE TABLE IF NOT EXISTS alugueis (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id           UUID NOT NULL REFERENCES clientes(id),
    equipamento_id       UUID NOT NULL REFERENCES equipamentos(id),
    data_inicio          DATE NOT NULL,
    data_fim_prevista    DATE NOT NULL,
    data_fim_real        DATE,
    modalidade           TEXT NOT NULL CHECK (modalidade IN ('diaria','mensal')),
    valor_contratado     NUMERIC(10,2) NOT NULL,
    valor_total_previsto NUMERIC(10,2) NOT NULL,
    valor_multa_dia      NUMERIC(10,2) NOT NULL DEFAULT 0,
    dias_atraso          INTEGER GENERATED ALWAYS AS (
        CASE WHEN data_fim_real IS NOT NULL AND data_fim_real > data_fim_prevista
             THEN (data_fim_real - data_fim_prevista) ELSE 0 END
    ) STORED,
    valor_multa_total    NUMERIC(10,2) GENERATED ALWAYS AS (
        CASE WHEN data_fim_real IS NOT NULL AND data_fim_real > data_fim_prevista
             THEN (data_fim_real - data_fim_prevista) * valor_multa_dia ELSE 0 END
    ) STORED,
    status               TEXT NOT NULL DEFAULT 'ativo'
                             CHECK (status IN ('ativo','devolvido','atrasado','cancelado')),
    observacoes          TEXT,
    criado_em            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Impede double-booking: mesmo equipamento com dois aluguéis ativos
CREATE UNIQUE INDEX IF NOT EXISTS idx_equipamento_aluguel_ativo
    ON alugueis(equipamento_id) WHERE status IN ('ativo','atrasado');

CREATE INDEX IF NOT EXISTS idx_alugueis_cliente ON alugueis(cliente_id);
CREATE INDEX IF NOT EXISTS idx_alugueis_status  ON alugueis(status);

-- =============================================================
-- TABELA: termos_responsabilidade
-- =============================================================
CREATE TABLE IF NOT EXISTS termos_responsabilidade (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluguel_id UUID NOT NULL REFERENCES alugueis(id),
    token      TEXT NOT NULL UNIQUE DEFAULT encode(gen_random_bytes(24), 'hex'),
    status     TEXT NOT NULL DEFAULT 'pendente'
                   CHECK (status IN ('pendente','aceito','expirado')),
    ip_aceite  TEXT,
    user_agent TEXT,
    aceito_em  TIMESTAMPTZ,
    pdf_path   TEXT,
    expira_em  TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
-- TABELA: pagamentos
-- =============================================================
CREATE TABLE IF NOT EXISTS pagamentos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluguel_id      UUID NOT NULL REFERENCES alugueis(id),
    descricao       TEXT NOT NULL,
    valor           NUMERIC(10,2) NOT NULL,
    data_vencimento DATE NOT NULL,
    data_pagamento  DATE,
    status          TEXT NOT NULL DEFAULT 'pendente'
                        CHECK (status IN ('pendente','pago','vencido','cancelado')),
    tipo            TEXT NOT NULL DEFAULT 'mensalidade'
                        CHECK (tipo IN ('mensalidade','diaria','multa','outros')),
    observacoes     TEXT,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pagamentos_aluguel    ON pagamentos(aluguel_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_status     ON pagamentos(status);
CREATE INDEX IF NOT EXISTS idx_pagamentos_vencimento ON pagamentos(data_vencimento);

-- =============================================================
-- TRIGGER: sincroniza status do equipamento com o aluguel
-- =============================================================
CREATE OR REPLACE FUNCTION sync_equipamento_status()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status IN ('ativo','atrasado') THEN
        UPDATE equipamentos SET status = 'alugado', atualizado_em = NOW()
        WHERE id = NEW.equipamento_id;
    ELSIF NEW.status IN ('devolvido','cancelado') THEN
        UPDATE equipamentos SET status = 'disponivel', atualizado_em = NOW()
        WHERE id = NEW.equipamento_id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_aluguel_status ON alugueis;
CREATE TRIGGER trg_aluguel_status
AFTER INSERT OR UPDATE OF status ON alugueis
FOR EACH ROW EXECUTE FUNCTION sync_equipamento_status();

-- =============================================================
-- RPC: estatísticas para o dashboard
-- =============================================================
CREATE OR REPLACE FUNCTION get_dashboard_stats()
RETURNS JSON LANGUAGE sql AS $$
    SELECT json_build_object(
        'receita_mes',              COALESCE((
            SELECT SUM(valor) FROM pagamentos
            WHERE status = 'pago'
              AND date_trunc('month', data_pagamento) = date_trunc('month', NOW())
        ), 0),
        'a_receber',                COALESCE((
            SELECT SUM(valor) FROM pagamentos WHERE status IN ('pendente','vencido')
        ), 0),
        'alugueis_ativos',          (SELECT COUNT(*) FROM alugueis WHERE status = 'ativo'),
        'alugueis_atrasados',       (SELECT COUNT(*) FROM alugueis WHERE status = 'atrasado'),
        'equipamentos_disponiveis', (SELECT COUNT(*) FROM equipamentos WHERE status = 'disponivel'),
        'termos_pendentes',         (SELECT COUNT(*) FROM termos_responsabilidade WHERE status = 'pendente')
    );
$$;

-- =============================================================
-- USUÁRIO ADMIN INICIAL
-- Senha: admin123 (troque imediatamente após o primeiro acesso)
-- Hash gerado com bcrypt, 12 rounds
-- =============================================================
INSERT INTO usuarios (nome, email, senha_hash, perfil)
VALUES (
    'Administrador',
    'admin@starlink.local',
    '$2b$12$3voQ5Erq.nCFBcq1K/lUNuL.R46/LCHDe9hh0jRFMWD9PwsIWb/.u',
    'admin'
)
ON CONFLICT (email) DO NOTHING;
