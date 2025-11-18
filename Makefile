# Variables
COMPOSE_FILE = docker-compose.yml
COMPOSE_DEV_FILE = docker-compose.dev.yml

# Construcción
build:
	docker compose -f $(COMPOSE_FILE) build

build-dev:
	docker compose -f $(COMPOSE_DEV_FILE) build -d

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

down:
	docker compose -f $(COMPOSE_FILE) down

stop:
	docker compose -f $(COMPOSE_FILE) stop

stop-dev:
	docker compose -f $(COMPOSE_DEV_FILE) stop

# Utilidades
logs:
	docker compose -f $(COMPOSE_DEV_FILE) logs -f

logs-app:
	docker compose -f $(COMPOSE_DEV_FILE) logs -f app


# Acceso a servicios
db:
	docker exec -it cisnatura_db_dev psql -U user -d cisnatura

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
	docker exec -it cisnatura_redis_dev redis-cli

mailhog:
	@echo "📧 Abriendo MailHog Web UI..."
	@echo "URL: http://localhost:8025"
	@open http://localhost:8025 || xdg-open http://localhost:8025 || echo "Abre manualmente: http://localhost:8025"

# Base de datos
db-init:
	docker exec -it cisnatura_app_dev python -m scripts.init_db

db-reset:
	@echo "⚠️  Esto eliminará todas las tablas y las volverá a crear"
	@read -p "¿Estás seguro? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker exec -it cisnatura_app_dev python -c "from scripts.init_db import drop_db, init_db; drop_db(); init_db()"; \
	else \
		echo "Operación cancelada"; \
	fi

db-seed:
	@echo "🌱 Poblando base de datos con datos de ejemplo..."
	docker exec -it cisnatura_app_dev python -m scripts.seed_db

clean:
	docker compose -f $(COMPOSE_DEV_FILE) down -v
	docker compose -f $(COMPOSE_FILE) down -v