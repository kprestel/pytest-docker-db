#!/bin/bash
set -e
psql -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER test WITH PASSWORD 'foo';
    ALTER USER hhs WITH SUPERUSER;
    CREATE DATABASE docker-test;
    GRANT ALL PRIVILEGES ON DATABASE docker-test TO test;
EOSQL



