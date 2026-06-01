-- ═══════════════════════════════════════════════════════════
-- INVENIO — Initialisation PostgreSQL
-- Exécuté automatiquement au premier démarrage du container
-- ═══════════════════════════════════════════════════════════

-- NocoDB (base principale déjà créée par POSTGRES_DB)
-- On crée les autres bases pour n8n, Windmill, Metabase

\connect postgres

CREATE DATABASE db_n8n
    WITH OWNER = invenio
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8';

CREATE DATABASE db_windmill
    WITH OWNER = invenio
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8';

CREATE DATABASE db_metabase
    WITH OWNER = invenio
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8';

-- Extensions utiles
\connect db_nocodb
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- Pour la recherche fuzzy

\connect db_n8n
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\connect db_windmill
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
