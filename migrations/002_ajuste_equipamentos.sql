-- Migração: converte vencimento_mensalidade de DATE para SMALLINT (dia 1-31)
-- e remove campos data_aquisicao e valor_aquisicao

ALTER TABLE equipamentos
    ADD COLUMN vencimento_dia SMALLINT CHECK (vencimento_dia BETWEEN 1 AND 31);

UPDATE equipamentos
SET vencimento_dia = EXTRACT(DAY FROM vencimento_mensalidade)::SMALLINT
WHERE vencimento_mensalidade IS NOT NULL;

ALTER TABLE equipamentos
    DROP COLUMN vencimento_mensalidade,
    DROP COLUMN data_aquisicao,
    DROP COLUMN valor_aquisicao;

ALTER TABLE equipamentos
    RENAME COLUMN vencimento_dia TO vencimento_mensalidade;
