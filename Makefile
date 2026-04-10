# MyBookshelfAI — run API + Vite dev servers; release ports on Ctrl+C or via `make stop`.

BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 5173
PYTHON ?= python3
FRONTEND_DIR := $(CURDIR)/frontend

.PHONY: help dev website backend frontend stop desktop-dev desktop-build

# Install JS deps when missing or after package-lock.json changes.
$(FRONTEND_DIR)/node_modules/.bin/vite: $(FRONTEND_DIR)/package-lock.json
	cd "$(FRONTEND_DIR)" && npm ci

help:
	@echo "Targets:"
	@echo "  make dev       – API (:$(BACKEND_PORT)) + Vite (:$(FRONTEND_PORT)); Ctrl+C stops both"
	@echo "  make website   – same as dev"
	@echo "  make backend   – API only"
	@echo "  make frontend  – Vite only"
	@echo "  make stop      – kill anything listening on those ports"
	@echo "  make desktop-dev   – Linux desktop app dev mode (Tauri)"
	@echo "  make desktop-build – Linux desktop build (Tauri)"
	@echo "Override Python: make PYTHON=.venv/bin/python dev"

# Run both servers in one shell so INT/TERM kills all background jobs and frees ports.
dev website: $(FRONTEND_DIR)/node_modules/.bin/vite
	set -e; \
	trap 'kill $$(jobs -p) 2>/dev/null || true; wait 2>/dev/null || true' INT TERM EXIT; \
	cd "$(CURDIR)" && PYTHONPATH=. $(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port $(BACKEND_PORT) & \
	cd "$(CURDIR)/frontend" && npm run dev & \
	wait || true; \
	kill $$(jobs -p) 2>/dev/null || true; \
	wait 2>/dev/null || true

backend:
	cd "$(CURDIR)" && PYTHONPATH=. $(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port $(BACKEND_PORT)

frontend: $(FRONTEND_DIR)/node_modules/.bin/vite
	cd "$(FRONTEND_DIR)" && npm run dev

desktop-dev: $(FRONTEND_DIR)/node_modules/.bin/vite
	cd "$(FRONTEND_DIR)" && npm run desktop:dev

desktop-build: $(FRONTEND_DIR)/node_modules/.bin/vite
	cd "$(FRONTEND_DIR)" && npm run desktop:build

stop:
	@for p in $(BACKEND_PORT) $(FRONTEND_PORT); do \
		if command -v fuser >/dev/null 2>&1; then \
			fuser -k "$$p/tcp" 2>/dev/null && echo "Freed port $$p" || true; \
		else \
			lp=$$(lsof -t -i:"$$p" -sTCP:LISTEN 2>/dev/null || true); \
			if [ -n "$$lp" ]; then \
				echo "$$lp" | xargs -r kill 2>/dev/null || true; \
				sleep 0.2; \
				lp=$$(lsof -t -i:"$$p" -sTCP:LISTEN 2>/dev/null || true); \
				[ -n "$$lp" ] && echo "$$lp" | xargs -r kill -9 2>/dev/null || true; \
				echo "Freed port $$p"; \
			fi; \
		fi; \
	done
