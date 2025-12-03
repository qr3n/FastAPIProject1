.PHONY: help db-up db-down db-restart db-logs full-up full-down full-restart full-logs backend-shell db-shell clean

help:
	@echo "Available commands:"
	@echo "  make db-up          - Start only database (PostgreSQL + pgAdmin)"
	@echo "  make db-down        - Stop database"
	@echo "  make db-restart     - Restart database"
	@echo "  make db-logs        - View database logs"
	@echo ""
	@echo "  make full-up        - Start full stack (DB + Backend + Frontend)"
	@echo "  make full-down      - Stop full stack"
	@echo "  make full-restart   - Restart full stack"
	@echo "  make full-logs      - View all logs"
	@echo ""
	@echo "  make backend-shell  - Enter backend container shell"
	@echo "  make db-shell       - Enter PostgreSQL shell"
	@echo "  make clean          - Remove all containers and volumes"

db-up:
	docker compose up -d
	@echo "✅ Database started!"
	@echo "📊 PostgreSQL: localhost:5432"
	@echo "🔧 pgAdmin: http://localhost:5050 (admin@dish.local / admin)"

db-down:
	docker compose down
	@echo "✅ Database stopped!"

db-restart:
	docker compose restart
	@echo "✅ Database restarted!"

db-logs:
	docker compose logs -f

full-up:
	docker compose -f docker-compose.full.yml up -d --build
	@echo "✅ Full stack started!"
	@echo "🔙 Backend: http://localhost:8000"
	@echo "🎨 Frontend: http://localhost:3000"
	@echo "📊 PostgreSQL: localhost:5432"
	@echo "🔧 pgAdmin: http://localhost:5050"

full-down:
	docker compose -f docker-compose.full.yml down
	@echo "✅ Full stack stopped!"

full-restart:
	docker compose -f docker-compose.full.yml restart
	@echo "✅ Full stack restarted!"

full-logs:
	docker-compose -f docker-compose.full.yml logs -f

backend-shell:
	docker exec -it dish_backend /bin/bash

db-shell:
	docker exec -it dish_postgres psql -U dish_user -d dish_db

clean:
	docker compose -f docker-compose.full.yml down -v
	docker compose down -v
	@echo "✅ All containers and volumes removed!"