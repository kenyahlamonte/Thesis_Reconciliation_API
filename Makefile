install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

test:
	pytest -q

clean:
	rm -rf __pycache__ .pytest_cache