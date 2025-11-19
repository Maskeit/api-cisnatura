# Variables
COMPOSE_FILE = docker-compose.yml
COMPOSE_DEV_FILE = docker-compose.dev.yml

# Detectar entorno (verificando si existe el contenedor dev)
DEV_CONTAINER := $(shell docker ps -q -f name=cisnatura_db_dev 2>/dev/null)
ifneq ($(DEV_CONTAINER),)
	ENV = dev
	DB_CONTAINER = cisnatura_db_dev
	APP_CONTAINER = cisnatura_app_dev
	REDIS_CONTAINER = cisnatura_redis_dev
else
	ENV = prod
	DB_CONTAINER = cisnatura_db
	APP_CONTAINER = cisnatura_app
	REDIS_CONTAINER = cisnatura_redis
endif

# Construcción
build:
	docker compose -f $(COMPOSE_FILE) build

build-dev:
	docker compose -f $(COMPOSE_DEV_FILE) build

# Desarrollo
dev:
	docker compose -f $(COMPOSE_DEV_FILE) up -d

dev-build:
	docker compose -f $(COMPOSE_DEV_FILE) up -d --build

dev-down:
	docker compose -f $(COMPOSE_DEV_FILE) down

# Producción
prod:
	docker compose -f $(COMPOSE_FILE) up -d

prod-build:
	docker compose -f $(COMPOSE_FILE) up -d --build

down:
	docker compose -f $(COMPOSE_FILE) down

stop:
	docker compose -f $(COMPOSE_FILE) stop

stop-dev:
	docker compose -f $(COMPOSE_DEV_FILE) stop

# Utilidades
logs:
	@if [ "$(ENV)" = "dev" ]; then \
		docker compose -f $(COMPOSE_DEV_FILE) logs -f; \
	else \
		docker compose -f $(COMPOSE_FILE) logs -f; \
	fi

logs-app:
	docker logs -f $(APP_CONTAINER)

logs-db:
	docker logs -f $(DB_CONTAINER)

# Info del entorno
info:
	@echo "🔍 Entorno detectado: $(ENV)"
	@echo "📦 Contenedores:"
	@echo "  - App:   $(APP_CONTAINER)"
	@echo "  - DB:    $(DB_CONTAINER)"
	@echo "  - Redis: $(REDIS_CONTAINER)"
	@echo ""
	@echo "📊 Estado de contenedores:"
	@docker ps --filter "name=cisnatura" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Acceso a servicios (auto-detecta entorno)
db:
	@echo "🔗 Conectando a PostgreSQL ($(ENV))..."
	docker exec -it $(DB_CONTAINER) psql -U user -d cisnatura

db-help:
	@echo "📚 Comandos básicos de PostgreSQL (psql):"
	@echo ""
	@echo "  Listar bases de datos:"
	@echo "    \\l  o  \\list"
	@echo ""
	@echo "  Conectar a una base de datos:"
	@echo "    \\c nombre_bd"
	@echo ""
	@echo "  Listar tablas:"
	@echo "    \\dt"
	@echo ""
	@echo "  Describir una tabla:"
	@echo "    \\d nombre_tabla"
	@echo ""
	@echo "  Listar esquemas:"
	@echo "    \\dn"
	@echo ""
	@echo "  Ejecutar SQL desde archivo:"
	@echo "    \\i ruta/archivo.sql"
	@echo ""
	@echo "  Ver historial de comandos:"
	@echo "    \\s"
	@echo ""
	@echo "  Salir:"
	@echo "    \\q  o  exit"
	@echo ""
	@echo "  Consultas SQL comunes:"
	@echo "    SELECT * FROM tabla;"
	@echo "    SELECT * FROM tabla LIMIT 10;"
	@echo "    SELECT COUNT(*) FROM tabla;"
	@echo "    TRUNCATE tabla;"
	@echo ""

redis:
	@echo "🔗 Conectando a Redis ($(ENV))..."
	docker exec -it $(REDIS_CONTAINER) redis-cli

redis-flush:
	@echo "⚠️  Esto limpiará TODOS los datos de Redis"
	@read -p "¿Estás seguro? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker exec -it $(REDIS_CONTAINER) redis-cli FLUSHALL; \
		echo "✅ Redis limpiado"; \
	else \
		echo "❌ Operación cancelada"; \
	fi

mailhog:
	@echo "📧 Abriendo MailHog Web UI..."
	@echo "URL: http://localhost:8025"
	@open http://localhost:8025 || xdg-open http://localhost:8025 || echo "Abre manualmente: http://localhost:8025"

# Base de datos
db-init:
	@echo "🔧 Inicializando base de datos en $(ENV)..."
	docker exec -it $(APP_CONTAINER) python -m scripts.init_db

db-reset:
	@echo "⚠️  Esto eliminará todas las tablas y las volverá a crear ($(ENV))"
	@read -p "¿Estás seguro? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker exec -it $(APP_CONTAINER) python -c "from scripts.init_db import drop_db, init_db; drop_db(); init_db()"; \
		echo "✅ Base de datos reiniciada"; \
	else \
		echo "❌ Operación cancelada"; \
	fi

db-seed:
	@echo "🌱 Poblando base de datos con datos de ejemplo ($(ENV))..."
	docker exec -it $(APP_CONTAINER) python -m scripts.seed_db

db-migrate:
	@echo "📝 Ejecutando migración de órdenes ($(ENV))..."
	docker exec -i $(DB_CONTAINER) psql -U user -d cisnatura < migration_orders.sql
	@echo "✅ Migración completada"

# Backup y restore
db-backup:
	@echo "💾 Creando backup de la base de datos..."
	@mkdir -p backups
	docker exec $(DB_CONTAINER) pg_dump -U user cisnatura > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup guardado en backups/"

db-restore:
	@echo "📥 Restaurar backup"
	@ls -1 backups/*.sql 2>/dev/null || echo "No hay backups disponibles"
	@read -p "Nombre del archivo (ej: backup_20240115_120000.sql): " file; \
	if [ -f "backups/$$file" ]; then \
		docker exec -i $(DB_CONTAINER) psql -U user -d cisnatura < backups/$$file; \
		echo "✅ Backup restaurado"; \
	else \
		echo "❌ Archivo no encontrado"; \
	fi

# Limpieza
clean:
	@echo "🧹 Limpiando contenedores y volúmenes..."
	docker compose -f $(COMPOSE_DEV_FILE) down -v
	docker compose -f $(COMPOSE_FILE) down -v
	@echo "✅ Limpieza completa"

clean-images:
	@echo "🗑️  Eliminando imágenes de Cisnatura..."
	docker images | grep cisnatura | awk '{print $$3}' | xargs -r docker rmi -f
	@echo "✅ Imágenes eliminadas"

# Ayuda
help:
	@echo "🚀 Comandos disponibles del Makefile:"
	@echo ""
	@echo "📦 Construcción:"
	@echo "  make build         - Construir imagen de producción"
	@echo "  make build-dev     - Construir imagen de desarrollo"
	@echo ""
	@echo "🔧 Desarrollo:"
	@echo "  make dev           - Levantar entorno de desarrollo"
	@echo "  make dev-build     - Reconstruir y levantar desarrollo"
	@echo "  make dev-down      - Detener desarrollo"
	@echo "  make stop-dev      - Pausar desarrollo"
	@echo ""
	@echo "🚀 Producción:"
	@echo "  make prod          - Levantar entorno de producción"
	@echo "  make prod-build    - Reconstruir y levantar producción"
	@echo "  make down          - Detener producción"
	@echo "  make stop          - Pausar producción"
	@echo ""
	@echo "📊 Logs:"
	@echo "  make logs          - Ver logs de todos los servicios"
	@echo "  make logs-app      - Ver logs de la aplicación"
	@echo "  make logs-db       - Ver logs de PostgreSQL"
	@echo ""
	@echo "🔗 Acceso a servicios:"
	@echo "  make db            - Conectar a PostgreSQL"
	@echo "  make redis         - Conectar a Redis"
	@echo "  make mailhog       - Abrir interfaz de MailHog"
	@echo "  make info          - Ver info del entorno actual"
	@echo ""
	@echo "🗄️  Base de datos:"
	@echo "  make db-init       - Crear tablas iniciales"
	@echo "  make db-reset      - Eliminar y recrear todas las tablas"
	@echo "  make db-seed       - Poblar con datos de ejemplo"
	@echo "  make db-migrate    - Ejecutar migración de órdenes"
	@echo "  make db-backup     - Crear backup de la base de datos"
	@echo "  make db-restore    - Restaurar backup"
	@echo "  make db-help       - Ayuda de comandos PostgreSQL"
	@echo ""
	@echo "🧹 Limpieza:"
	@echo "  make clean         - Eliminar contenedores y volúmenes"
	@echo "  make clean-images  - Eliminar imágenes de Docker"
	@echo "  make redis-flush   - Limpiar toda la caché de Redis"
	@echo ""
	@echo "ℹ️  Ayuda:"
	@echo "  make help          - Mostrar esta ayuda"
	@echo ""

.PHONY: build build-dev dev dev-build dev-down prod prod-build down stop stop-dev \
        logs logs-app logs-db info db db-help redis redis-flush mailhog \
        db-init db-reset db-seed db-migrate db-backup db-restore \
        clean clean-images help

.DEFAULT_GOAL := help
