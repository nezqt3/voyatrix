.PHONY: parse start

start:
	python -m app.main

parse:
	python -m aggregation.main
