-- Оценка качества лида: насколько целевой (1-5) и насколько нам подходит (1-5)
ALTER TABLE leads ADD COLUMN qual_score INTEGER DEFAULT NULL;
ALTER TABLE leads ADD COLUMN fit_score INTEGER DEFAULT NULL;
ALTER TABLE leads ADD COLUMN qual_notes TEXT DEFAULT NULL;
