.PHONY: up logs test deploy

up:
	docker compose up -d

logs:
	docker compose logs -f

test:
	docker compose -f docker-compose.test.yml up -d
	cd backend && pytest
	docker compose -f docker-compose.test.yml down

deploy:
	@echo "Deployment target not yet fully configured"
