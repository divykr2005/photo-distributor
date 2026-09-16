.PHONY: up dev dev-logs logs test deploy

up:
	docker compose up -d

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

dev-logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

logs:
	docker compose logs -f

test:
	docker compose -f docker-compose.test.yml up -d
	cd backend && python -m pytest; status=$$?; cd ..; docker compose -f docker-compose.test.yml down; exit $$status

deploy:
	@echo "Deployment target not yet fully configured"
