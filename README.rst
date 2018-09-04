=============
ckanext-updateschema
=============

CKAN extension to create custom fields for City of Toronto Open Data Portal

------------
Installation
------------

To install ckanext-updateschema:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-updateschema Python package into your virtual environment::

     pip install ckanext-updateschema

3. Add ``updateschema`` to the ``ckan.plugins`` setting in your CKAN config file (by default the config file is located at ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload
