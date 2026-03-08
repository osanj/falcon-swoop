#!/bin/bash
EXAMPLE_PORT=${PORT:-8080}
gunicorn --bind 127.0.0.1:${EXAMPLE_PORT} --reload "falcon_swoop_example.app:build(${EXAMPLE_PORT})"
