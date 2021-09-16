# -*- coding: utf-8 -*-
from setuptools import setup, find_packages  # Always prefer setuptools over distutils
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="""ckanext-opendatatoronto""",
    version="2.2.0",
    description="""
        This extension contains plugins that modifiy and extend default CKAN features for the City of Toronto Open Data Portal.
    """,
    long_description=long_description,
    url="https://github.com/open-data-toronto/ckan-customization-open-data-toronto",
    author="""Open Data Toronto""",
    author_email="""opendata@toronto.ca""",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
    ],
    keywords="",
    packages=find_packages(exclude=["contrib", "docs", "tests*"]),
    namespace_packages=["ckanext"],
    install_requires=[],
    include_package_data=True,
    package_data={},
    data_files=[],
    entry_points="""
        [ckan.plugins]
        managepackageschema=ckanext.opendata.plugin:ManagePackageSchemaPlugin
        updateschema=ckanext.opendata.plugin:UpdateSchemaPlugin
        extendedurl=ckanext.opendata.plugin:ExtendedURLPlugin
        extendedapi=ckanext.opendata.plugin:ExtendedAPIPlugin

        [babel.extractors]
        ckan = ckan.lib.extract:extract_ckan
    """,
    message_extractors={
        "ckanext": [
            ("**.py", "python", None),
            ("**.js", "javascript", None),
            ("**/templates/**.html", "ckan", None),
        ],
    },
)
