-- Cria tabela de pacotes com desconto por duração exata
-- Limpa faixas antigas e mantém somente a diária base por plano
CREATE TABLE IF NOT EXISTS pacotes_diaria (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo_plano    VARCHAR(20) NOT NULL,
    dias          INTEGER NOT NULL CHECK (dias > 0),
    valor_total   NUMERIC(10,2) NOT NULL CHECK (valor_total > 0),
    ativo         BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_pacote UNIQUE (tipo_plano, dias)
);

DELETE FROM faixas_preco_diaria;
INSERT INTO faixas_preco_diaria (dias_min, dias_max, valor_por_dia, tipo_plano) VALUES
(1, 9999, 40.00, '100GB'),
(1, 1,    90.00, 'ILIMITADO'),
(2, 4,    80.00, 'ILIMITADO');

INSERT INTO pacotes_diaria (tipo_plano, dias, valor_total) VALUES
('100GB',     5,  180.00),
('100GB',    10,  300.00),
('100GB',    15,  375.00),
('100GB',    30,  450.00),
('ILIMITADO', 5,  350.00),
('ILIMITADO',10,  550.00),
('ILIMITADO',15,  675.00),
('ILIMITADO',30,  900.00);
