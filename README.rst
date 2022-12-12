=============
ckanext-opendatatoronto
=============

------------
Description
------------

This extension contains plugins that modifiy and extend default CKAN features to integrate with the City of Toronto Open Data Portal. These plugins includes:

* **updateschema**: Extends package schema to include custom fields used to maintain datasets published on the OD Portal. This plugin also contains validations and triggers to automate and manage the contents of these new fields.

* **extendedapi**: Extends the action API to include new endpoints to enhance the OD Portal functionalities, most notably of which is the `/datastore_cache` functionality, which creates multiple formats / CSRs of filestore resources from newly created/updated datastore resources.

* **extendedtheme**: Extends default CKAN templates to include basic changes to the CKAN homepage. This allows CKAN admins to view and search CoT OD's custom `od_etl_inventory` dataset directly on the homepage


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

5. Add any of the plugins listed above to the `ckan.plugins` setting in your CKAN config file (by default the config file is located at ``/etc/ckan/default/production.ini``).

6. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload

------------
Additional Endpoints and URLs
------------
This extension uses CKAN's IActions plugin interface to add the following useful api endpoints:

* ``/api/action/quality_show?package_id={package_id}``: Returns data quality score for the input package, as calculated by an external function
* ``/api/action/search_packages``: Returns package list based on solr attributes appended to the api call url. This is used for the search bars on https://open.toronto.ca
* ``/api/action/datastore_cache``: Allows authorized user to create filestore resources (for the purpose of downloading later) for an input datastore resource, in multiple formats. This extension has an additional hook on the native ``datastore_create`` endpoint that, under certain circumstances, prompts the firing of the ``/datastore_cache`` endpoint

------------
A note on /datastore_cache
------------
Datastore caching is how we enable users to download large datasets quickly.

For a user to get a large datastore resource from CKAN as a file download, the server needs to get the data from CKAN and translate it into the file format (and, for geospatial datasets, Coordinate Reference System) requested by the user. ``/datastore_cache``, which relies heavily on https://github.com/open-data-toronto/ckanext-iotrans, allows CKAN to transform and cache those files long before a user requests that data.

By default, ``/datastore_cache`` is run after a datastore resource is updated ... but it can also be run on demand.


------------
Contribution
------------

Please contact opendata@toronto.ca
