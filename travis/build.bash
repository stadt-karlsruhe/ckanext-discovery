#!/bin/bash

set -e

echo "This is travis-build.bash..."

#
# CKAN
#

echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install postgresql-$PGVERSION solr-tomcat libcommons-fileupload-java:amd64=1.2.2-1

echo "Installing CKAN and its Python dependencies..."
git clone https://github.com/ckan/ckan
cd ckan
export latest_ckan_release_branch=`git branch --all | grep remotes/origin/release-v | sort -r | sed 's/remotes\/origin\///g' | head -n 1`
echo "CKAN branch: $latest_ckan_release_branch"
git checkout $latest_ckan_release_branch
python setup.py develop
pip install -r requirements.txt --allow-all-external
pip install -r dev-requirements.txt --allow-all-external
pip install coveralls
cd -

echo "Moving test.ini into a subdir..."
mkdir subdir
mv test.ini subdir

#
# CKANEXT-DISCOVERY
#

echo "Installing ckanext-discovery and its requirements..."
python setup.py develop
pip install -r dev-requirements.txt

#
# SOLR
#

echo "Configuring Solr"
sudo cp solr/* /etc/solr/conf/
# The name of the Tomcat service depends on the currently installed version
TOMCAT_SERVICE=$(sudo service --status-all 2>&1 | awk '/tomcat/ { print $4 }')
echo "Tomcat's service is $TOMCAT_SERVICE"
sudo service $TOMCAT_SERVICE restart

#
# POSTGRESQL
#

echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'

echo "Initialising CKAN database..."
paster --plugin=ckan db init -c subdir/test.ini

echo "Initializing ckanext-discovery database tables..."
paster --plugin=ckanext-discovery search_suggestions init -c subdir/test.ini

echo "travis-build.bash is done."

