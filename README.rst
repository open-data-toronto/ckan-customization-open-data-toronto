=============
ckanext-opendatatoronto
=============

CKAN extension to create custom fields for City of Toronto Open Data Portal

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
