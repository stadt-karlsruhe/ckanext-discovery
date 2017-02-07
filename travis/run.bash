#!/bin/bash

set -e

nosetests --ckan \
          --nocapture \
          --nologcapture \
          --with-pylons=subdir/test.ini \
          --with-coverage \
          --cover-package=ckanext.discovery \
          --cover-inclusive \
          --cover-erase

