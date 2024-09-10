#!/bin/sh

REPORT_FILE=CKAN_Open_Data_Toronto_Extension.xml
pytest --junitxml=$REPORT_FILE

sed -i 's/hostname="[^"]*"//g' $REPORT_FILE
