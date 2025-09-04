#!/bin/bash
gunicorn storebuilder.wsgi:application --bind 0.0.0.0:8080 --workers 3 --timeout 120