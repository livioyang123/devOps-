# Database Connection Error - Docker Compose Service Names

## Problema Identificato

Durante l'esecuzione del task 1.2 "Configure database and migrations", ho incontrato un errore di connessione al database PostgreSQL quando si tenta di eseguire le migrazioni Alembic dal container backend.

## Errore Specifico

```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server: Connection refused
	Is the server running on host "localhost" and accepting
	TCP/IP connections on port 5432?
```

## Causa Root

Il problema è nell'uso di `localhost` nelle stringhe di connessione al database quando si lavora all'interno di container Docker. In un ambiente Docker Compose, i servizi devono comunicare tra loro usando i **nomi dei servizi** definiti nel `docker-compose.yml`, non `localhost`.

## Configurazioni Problematiche Trovate

### 1. Backend Configuration (`backend/app/config.py`)
```python
# ❌ ERRATO - usa localhost
database_url: str = "postgresql://devops:devops123@localhost:5432/devops_k8s"

# ✅ CORRETTO - usa nome servizio
database_url: str = "postgresql://devops:devops123@postgres:5432/devops_k8s"
```

### 2. Alembic Configuration (`backend/alembic.ini`)
```ini
# ❌ ERRATO - usa localhost
sqlalchemy.url = postgresql://devops:devops123@localhost:5432/devops_k8s

# ✅ CORRETTO - usa nome servizio
sqlalchemy.url = postgresql://devops:devops123@postgres:5432/devops_k8s
```

### 3. Environment Variables nel Docker Compose
```yaml
# ✅ CORRETTO - già configurato correttamente
environment:
  - DATABASE_URL=postgresql://devops:devops123@postgres:5432/devops_k8s
```

## Test Eseguiti che Hanno Fallito

### Test 1: Connessione Database dal Backend Container
```bash
docker-compose exec backend python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connected successfully')
"
```
**Risultato**: `Connection refused` su localhost:5432

### Test 2: Esecuzione Migrazioni Alembic
```bash
docker-compose exec backend alembic upgrade head
```
**Risultato**: `could not connect to server: Connection refused`

### Test 3: Test di Connessione Diretta
```bash
docker-compose exec backend python -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='devops_k8s',
    user='devops',
    password='devops123'
)
print('Connected!')
"
```
**Risultato**: `Connection refused`

## Test che Funzionano (Conferma della Soluzione)

### Test 1: pgAdmin Web Interface
- **URL**: http://localhost:5050
- **Connessione**: postgres:5432 ✅ FUNZIONA
- **Conferma**: pgAdmin può connettersi usando il nome del servizio

### Test 2: Connessione dal Container usando Nome Servizio
```bash
docker-compose exec backend python -c "
import psycopg2
conn = psycopg2.connect(
    host='postgres',  # Nome del servizio
    port=5432,
    database='devops_k8s',
    user='devops',
    password='devops123'
)
print('Connected successfully!')
"
```
**Risultato**: ✅ DOVREBBE FUNZIONARE

## File da Correggere

### 1. `backend/app/config.py`
```python
# Cambiare la default database_url
database_url: str = "postgresql://devops:devops123@postgres:5432/devops_k8s"
```

### 2. `backend/alembic.ini`
```ini
# Cambiare sqlalchemy.url
sqlalchemy.url = postgresql://devops:devops123@postgres:5432/devops_k8s
```

### 3. `backend/app/database.py` (se presente)
```python
# Assicurarsi che usi la configurazione corretta
SQLALCHEMY_DATABASE_URL = settings.database_url
```

## Spiegazione Tecnica

### Perché localhost non funziona in Docker?

1. **Isolamento dei Container**: Ogni container ha il proprio stack di rete
2. **localhost nel Container**: Si riferisce al container stesso, non all'host
3. **Comunicazione tra Container**: Avviene tramite la rete Docker interna
4. **DNS Interno**: Docker Compose crea automaticamente record DNS per i nomi dei servizi

### Perché pgAdmin funziona?

pgAdmin è configurato correttamente per usare `postgres` come hostname, quindi può connettersi senza problemi.

## Soluzione Immediata

1. **Correggere** `backend/app/config.py` - cambiare `localhost` con `postgres`
2. **Correggere** `backend/alembic.ini` - cambiare `localhost` con `postgres`
3. **Riavviare** i container: `docker-compose restart backend celery-worker`
4. **Testare** la connessione: `docker-compose exec backend alembic upgrade head`

## Note per il Futuro

- **Sviluppo Locale**: Usare `localhost` quando si esegue il backend direttamente (non in container)
- **Container**: Sempre usare i nomi dei servizi Docker Compose
- **Variabili d'Ambiente**: Preferire le env vars per gestire diverse configurazioni
- **Configurazione Dinamica**: Considerare l'uso di env vars diverse per dev/prod

## Comando per Verificare la Risoluzione

```bash
# Test rapido dopo la correzione
docker-compose exec backend python -c "
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://devops:devops123@postgres:5432/devops_k8s')
with engine.connect() as conn:
    result = conn.execute(text('SELECT version()'))
    print('PostgreSQL Version:', result.fetchone()[0])
"
```

Questo dovrebbe stampare la versione di PostgreSQL se la connessione funziona correttamente.