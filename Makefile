# MyBookshelfAI — run API + Vite dev servers; release ports on Ctrl+C or via `make stop`.

BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 5173
PYTHON ?= python3

.PHONY: help dev website backend frontend stop

help:
	@echo "Targets:"
	@echo "  make dev       – API (:$(BACKEND_PORT)) + Vite (:$(FRONTEND_PORT)); Ctrl+C stops both"
	@echo "  make website   – same as dev"
	@echo "  make backend   – API only"
	@echo "  make frontend  – Vite only"
	@echo "  make stop      – kill anything listening on those ports"
	@echo "Override Python: make PYTHON=.venv/bin/python dev"

# Run both servers in one shell so INT/TERM kills all background jobs and frees ports.
dev website:
	set -e; \
	trap 'kill $$(jobs -p) 2>/dev/null || true; wait 2>/dev/null || true' INT TERM EXIT; \
	cd "$(CURDIR)" && PYTHONPATH=. $(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port $(BACKEND_PORT) & \
	cd "$(CURDIR)/frontend" && npm run dev & \
	wait || true; \
	kill $$(jobs -p) 2>/dev/null || true; \
	wait 2>/dev/null || true

backend:
	cd "$(CURDIR)" && PYTHONPATH=. $(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port $(BACKEND_PORT)

frontend:
	cd "$(CURDIR)/frontend" && npm run dev

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
