install:
	pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload --port 8001

test:
	pytest -q

clean:
	rm -rf __pycache__ .pytest_cache