.PHONY: help backend mobile mobile-tunnel test test-backend test-frontend assets sync-ip

help:
	@echo "🪙 Penny Financial Assistant — Command Center"
	@echo ""
	@echo "Available commands:"
	@echo "  make backend         Start FastAPI backend server on 0.0.0.0:8000"
	@echo "  make mobile          Sync Wi-Fi LAN IP and start Expo mobile bundler"
	@echo "  make mobile-tunnel   Start Expo with Cloudflare tunnel (remote/cellular)"
	@echo "  make sync-ip         Detect current Wi-Fi IP and update frontend/.env"
	@echo "  make test            Run both backend and frontend test suites"
	@echo "  make test-backend    Run pytest test suite (175 tests)"
	@echo "  make test-frontend   Run frontend unit tests (6 tests)"
	@echo "  make assets          Rebuild all mobile OS brand assets and icons"
	@echo ""

backend:
	uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

mobile:
	@cd frontend && npm run start:mobile

mobile-tunnel:
	@cd frontend && npm run start:tunnel

sync-ip:
	@cd frontend && npm run sync-ip

test: test-backend test-frontend

test-backend:
	PYTHONPATH=. uv run pytest -v

test-frontend:
	@cd frontend && npm test

assets:
	@cd frontend && npm run build:assets
