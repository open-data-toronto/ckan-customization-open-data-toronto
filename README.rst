=======================
ckanext-opendatatoronto
=======================

------------
Description
------------

This extension contains plugins that modifiy and extend default CKAN features to integrate with the City of Toronto Open Data Portal. 

If you have any questions about this repo, you can ask us at opendata@toronto.ca

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

5. Add correct plugins setting in your CKAN config file (by default the config file is located at ``/etc/ckan/default/production.ini``).

6. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


--------------------------
A note on /datastore_cache
--------------------------
Datastore caching is how we enable users to download large datasets quickly.

For a user to get a large datastore resource from CKAN as a file download, the server needs to get the data from CKAN and translate it into the file format (and, for geospatial datasets, Coordinate Reference System) requested by the user. ``/datastore_cache``, which relies heavily on https://github.com/open-data-toronto/iotrans, allows CKAN to transform and cache those files long before a user wants that data.

By default, ``/datastore_cache`` is run after a datastore resource is updated ... but it can also be run on demand.


----------------------
Dependency management
----------------------

There are three requirements files:

* ``requirements.txt`` — this extension's own direct dependencies (loose bounds).
  Edit this file to add or change ``opendata_ckan``-specific deps. It is also
  used as ``install_requires`` in ``setup.py`` so other adopters get the right deps.
* ``requirements.in`` — aggregator for the full deployment stack (CKAN core,
  ``od-ckanext-iotrans``, ``ckanext-solr-sqs``, and production pin overrides).
  Edit this file only for cross-repo or deployment-specific changes.
* ``requirements-lock.txt`` — the fully compiled, pinned lockfile generated from
  ``requirements.in``. Do not edit it by hand.

The local Docker build and the CloudFormation deployment both consume
``requirements-lock.txt``.

To regenerate the lockfile after any change to ``requirements.txt`` or
``requirements.in``::

    bin/compile-requirements.sh

The script requires ``uv`` (recommended) or ``pip-tools``::

    # uv (install once):
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # or pip-tools:
    pip install pip-tools

Commit ``requirements.txt``, ``requirements.in``, and the regenerated
``requirements-lock.txt``.

------------
Contribution
------------

Please contact opendata@toronto.ca

------------------------
Developing and Debugging
------------------------

``pre-commit``
==============
This repository uses `pre-commit <https://pre-commit.com/>`_.

To set up:

.. code-block:: bash

    # Install pre-commit
    pip install -r dev-requirements.txt
    pre-commit install

Usage:

* after you've installed pre-commit, the next time you ``git commit`` the list of installed pre-commit hooks (defined in ``.pre-commit.yaml``) will run to auto-format files and check for other things.
* A log of hooks that succeeded and failed will be printed
* Normally a few will 'fail' which typically just means some rules of the hook were broken (e.g. a file in the diff had trailing whitepace)
* Most often, the hooks defined for this repo will automatically fix these issues: running ``git status`` should then show some newly-unstaged changes which resulted from the pre-commit hooks modifying files (eg. autoformatting)
* if an issue can't be automatically fixed by the installed hooks then you may need to fix it yourself before a commit is excepted
* pre-commit hooks can be bypassed with the ``-n`` flag: ``git commit -n -m "some commit message"``. This should generally be avoided if possible (if a rule truly should be ignored consider using linting ingore comments, eg ``# noqa:<flake8_rule_id>``

Testing
=======
This repository uses ``pytest``.

Running tests:
--------------

.. code-block:: bash

    # install dev dependencies
    pip install -r dev-requirements.txt
    # run the tests:
    pytest --ckan-ini=/path/to/ckan/config.ini


Note: specifying the ``--ckan-ini`` flag each time can be a bit tedious, you may prefer
to configure a ``CKAN_INI=/path/to/ckan/config.ini`` environment variable instead, and
then you can run just ``pytest``.

Contributing tests:
-------------------
Unlike some other CKAN extension testing norms, we do not always run unit tests against
an ephemeral empty DB for some infrastructure reasons (more normally tests will be run
against the db in your dev environment).


Other CKAN repos commonly use the ``clean_db`` test fixture which clobbers the database to
create a clean environment for testing. **NOTE**: we **do not** use this fixture because it
will corrupt our dev databases (due to present configurations of dev dbs/environments).


In lieu of an ephemeral testing DB, this repo defines several test fixtures (primarily
in ``conftest.py``) which can be used to create any temporary packages/resources/users,
etc... which are then cleaned up at the end of the test run. This provides some degree
of test isolation and aims to keep some distracting junk out of our dev dbs.
