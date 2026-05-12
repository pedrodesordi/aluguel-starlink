-- Adiciona custo mensal do plano Starlink por equipamento
ALTER TABLE equipamentos
    ADD COLUMN custo_mensalidade NUMERIC(10,2);
