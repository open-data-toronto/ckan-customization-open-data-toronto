=============
ckanext-opendatatoronto
=============

------------
Description
------------

This extension contains plugins that modifiy and extend default CKAN features to integrate with the City of Toronto Open Data Portal. These plugins includes:

* **updateschema**: Extends package schema to include custom fields used to maintain datasets published on the OD Portal. This plugin also contains validations and triggers to automate and manage the contents of these new fields.

* **extendedapi**: Extends the action API to include new endpoints to enhance the OD Portal functionalities, most notably of which is the `/datastore_cache` functionality, which creates multiple formats / CSRs of filestore resources from newly created/updated datastore resources.

* **extendedurl**: Extends the URLs to include new functions that are outside the scope of the APIs.


**NOTE**: Any issues found on the portal should be reported to opendata@toronto.ca

------------
Installation
------------
This section describes installing this extension in the context of an existing CKAN deployment. For more information on CKAN, go to https://ckan.org/ or http://docs.ckan.org/en/2.9/

To install ckanext-opendatatoronto:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Move to CKAN installation folder::

     cd /usr/lib/ckan/default/src

3. Clone the extension from GIT::

     git clone https://github.com/CityofToronto/ckan-customization-open-data-toronto.git ckanext-opendatatoronto

4. Install the ckanext-opendatatoronto Python package into your virtual environment::

     pip install -e ckanext-opendatatoronto

5. Add ``updateschema``, ``extendedurl`` and ``extendedapi`` to the ``ckan.plugins`` setting in your CKAN config file (by default the config file is located at ``/etc/ckan/default/production.ini``).

6. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload

------------
Additional Endpoints and URLs
------------
This extension uses CKAN's IActions plugin interface to add the following api endpoints:

* `/download_resource/{resource_id}`: Fetches and serves filestore and datastore content for resources and enables format and projection conversions for those resources that are in the datastore
* `/api/action/quality_show?package_id={package_id}`: Returns data quality score for the input package, as calculated by an external function
* `/api/action/search_packages`: Returns package list based on solr attributes appended to the api call url
* `/api/action/search_facet`: Returns dataset filters, AKA solr facets, based on solr attributes appended to the api call
* `/api/action/datastore_cache`: Allows authorized user to create filestore resources (for the purpose of downloading later) for an input datastore resource, in multiple formats
* `/api/action/datastore_cache`: This extension has an additional hook on the native `datastore_create` endpoint that, under certain circumstances, prompts the firing of the `/datastore_cache` endpoint
* `/api/action/reindex_solr`: Allows an authorized user to refresh the solr index

------------
Contribution
------------

Please contact opendata@toronto.ca
