=============
ckanext-opendatatoronto
=============

------------
Description
------------

This extension contains plugins that modifiy and extend default CKAN features to intergrate with the City of Toronto Open Data Portal. These plugins includes:

* **updateschema**: Extends package and resource schemas to include custom fields used to maintain datasets published on the OD Portal. This plugin also contains validations and triggers to automate and manage the contents of these new fields.

* **extendedapi**: Extends the action API to include new endpoints to enhance the OD Portal functionalities.

* **extendedurl**: Extends the URLs to include new functions that are outside the scope of the APIs.

**NOTE**: The City of Toronto Open Data Portal is a work in progress. See https://github.com/CityofToronto/ckan-customization-open-data-toronto/issues/ for list of known issues.

------------
Installation
------------

To install ckanext-opendatatoronto:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Move to CKAN installation folder::

     cd /usr/lib/ckan/default/src

3. Clone the extension from GIT::

     git clone https://github.com/CityofToronto/ckan-customization-open-data-toronto.git ckanext-opendatatoronto

4. Install the ckanext-opendatatoronto Python package into your virtual environment::

     pip install -e ckanext-opendatatoronto

5. Add ``updateschema`` and ``downloadstores`` to the ``ckan.plugins`` setting in your CKAN config file (by default the config file is located at ``/etc/ckan/default/production.ini``).

6. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload

------------
Additional Endpoints and URLs
------------

1. /api/3/action/catalogue_search: Converts input parameters from the frontend to SOLR queries to search the dataset catalogue

2. /download_resource/{resource_id}: Fetches and serves filestore and datastore content for resources and enables format and projection conversions for those resources that are in the datastore

3. /tags_autocomplete: Lists tags for specific vocabularies ordered by similarity between tag name and query term

------------
Contribution
------------

------------
License
------------
