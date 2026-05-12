-- Adiciona coluna tipo_plano em faixas_preco_diaria para separar preços por plano
ALTER TABLE faixas_preco_diaria
    ADD COLUMN tipo_plano VARCHAR(20) NOT NULL DEFAULT '100GB';
