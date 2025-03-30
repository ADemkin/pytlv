test:
	@pytest -v --capture=no --lf


fmt:
	@ruff check --fix .
	@ruff format .
