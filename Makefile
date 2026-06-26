# FraudShield AI — common tasks. Run `make help` for the list.
.PHONY: help install install-dev data data-large train run api streamlit stop \
        smoke test lint web-build ppt docker-up docker-down clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:      ## Install runtime dependencies
	pip install -r requirements.txt

install-dev:  ## Install dev/test/MLOps dependencies
	pip install -r requirements-dev.txt

data:         ## Generate the small synthetic sample dataset
	python src/make_sample_data.py

data-large:   ## Generate a large (~500k row) synthetic PaySim-style dataset
	python src/make_large_dataset.py

train:        ## Train all models (uses data/paysim.csv if present)
	python src/train_all.py

run:          ## Start API + Streamlit and open the browser
	./run.sh all

api:          ## Start only the FastAPI backend (serves the React app)
	./run.sh api

streamlit:    ## Start only the Streamlit dashboard
	./run.sh streamlit

stop:         ## Stop services started by run.sh
	./run.sh stop

smoke:        ## Run the API smoke test (asserts the demo is healthy)
	python scripts/smoke_test.py

test:         ## Run the unit/integration test suite
	pytest -q

lint:         ## Lint the Python source (ruff)
	ruff check src api scripts tests || true

web-build:    ## Build the React app into web/dist
	cd web && npm install && npm run build

ppt:          ## Generate the PowerPoint deck
	node presentation/generate_pptx.js

docker-up:    ## Start the full stack via docker-compose
	docker compose up --build

docker-down:  ## Stop the docker-compose stack
	docker compose down

clean:        ## Remove caches and generated artifacts (keeps models/reports)
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
