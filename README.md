# Dashboard Revenda

Dashboard para gestão e visualização de dados de revenda de carros.

## Stack

- **Backend**: Python + Django + Django REST Framework
- **Frontend**: a definir (placeholder)
- **Infra**: Docker / docker-compose — PostgreSQL

## Como rodar

> Instruções completas serão adicionadas nas próximas etapas, à medida que backend e frontend forem implementados.

1. Clonar o repositório
2. Copiar `.env.example` para `.env` e preencher as variáveis
   - `POSTGRES_PORT` usa `5433` por padrão para não colidir com um Postgres nativo (ex.: Homebrew) que já esteja ouvindo em `5432` na máquina. Se sua máquina não tem esse conflito, pode usar `5432` normalmente.
3. Subir o banco de dados: `docker compose up -d postgres`
   - Verificar que o container está saudável: `docker compose ps` (status `healthy`)
   - Conectar manualmente para validar: `psql -h localhost -p ${POSTGRES_PORT} -U <POSTGRES_USER> -d <POSTGRES_DB>`
4. Rodar o backend:
   ```bash
   cd backend
   python3 -m venv .venv        # se ainda não existir
   source .venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver
   ```
   - Settings modulares em `config/settings/` (`base.py`, `dev.py`, `prod.py`). `manage.py` usa `config.settings.dev` por padrão; em produção, defina `DJANGO_SETTINGS_MODULE=config.settings.prod`.
   - Documentação da API (drf-spectacular): `http://localhost:8000/api/docs/`
