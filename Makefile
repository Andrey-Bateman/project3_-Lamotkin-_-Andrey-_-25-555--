install:
	poetry install

project:
	poetry run project

build:
	poetry build

publish:
	poetry publish --dry-run

package-install:
	python3 -m pip install --user dist/*.whl	
lint:
	poetry run ruff check .
parser:
	poetry run python -m valutatrade_hub.parser_service.scheduler 

update-rates:
	poetry run python main.py update-rates 

show-rates:
	poetry run python main.py show-rates 
