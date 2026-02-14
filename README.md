# Database (Postgres) — local dev setup

Short reference for the local Postgres + pgAdmin configured for this repo.

## Files
- `docker-compose.yaml` (repo root) — defines services:
  - `db` (postgres:15)
  - `pgadmin` (dpage/pgadmin4)
- `.env` (repo root) — environment variables used by compose.

Example `.env` in this repo:
```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=db_name
PGADMIN_EMAIL=admin@admin.com
PGADMIN_PASSWORD=password
```

## Ports and networking
- Host → container mappings (as configured):
  - Host `5433` -> Container `5432` (Postgres)
  - Host `8080` -> Container `80` (pgAdmin)
- Inside Docker Compose network, `pgadmin` can connect to Postgres using service name `db` and port `5432`.


## Common commands (run from repo root)
Start services:
```bash
docker compose up -d
docker compose ps
```

Stop and remove:
```bash
docker compose down
```

View logs:
```bash
docker compose logs -f db
docker compose logs -f pgadmin
```

## pgAdmin connection
- Open: http://localhost:8080
- Sign in with `PGADMIN_EMAIL` / `PGADMIN_PASSWORD` from .env.
- Register a server:
  - General → Name: `guitar_safari` (or any name)
  - Connection:
    - Hostname/address: `db` (preferred when pgAdmin runs in the same compose project)
    - Port: `5432`
    - Maintenance DB: `postgres` (or `guitar_safari`)
    - Username: `postgres`
    - Password: `pw`
  - Alternatively, if connecting from host set Host to `localhost` and Port to `5433`.

## Python connection
Recommended stack:
- SQLAlchemy + psycopg (sync)
- Example DATABASE_URL (use in .env if you want the app to read it):
```
DATABASE_URL=postgresql+psycopg://postgres:pw@localhost:5433/guitar_safari
```

## Security reminder
- Add .env to .gitignore to avoid committing credentials.
- Use stronger passwords for any non-local deployments.

-- end
