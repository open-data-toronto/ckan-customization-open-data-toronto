def modify_package_schema(schema, convert_method):
    modifications = {
        # General dataset info (inputs)
        'collection_method': [utils.default_to_none],
        'excerpt': [utils.default_to_none, validate_length],
        'limitations': [utils.default_to_none],
        'information_url': [utils.default_to_none],
        # General dataset info (dropdowns)
        'dataset_category': [utils.default_to_none, convert_hex_to_string],
        'is_retired': [utils.default_to_false],
        'refresh_rate': [utils.default_to_none, convert_hex_to_string],
        # Filters
        'civic_issues': [utils.default_to_none],
        'formats': [utils.default_to_none],
        'topics': [utils.default_to_none],
        # Dataset division info
        'owner_division': [utils.default_to_none, convert_hex_to_string],
        'owner_section': [utils.default_to_none],
        'owner_unit': [utils.default_to_none],
        'owner_email': [utils.default_to_none],
        # Internal CKAN/WP fields
        'image_url': [utils.default_to_none],
        'last_refreshed': [utils.default_to_none]
    }

    for key, value in modifications.items():
        if convert_method == 'input':
            if key in ('civic_issues', 'formats', 'topics'):
                modifications[key].append(convert_string_to_tags)

            modifications[key].insert(1, tk.get_converter('convert_to_extras'))
        elif convert_method == 'output':
            if key in ('civic_issues', 'formats', 'topics'):
                modifications[key].append(convert_tags_to_string)

            modifications[key].insert(0, tk.get_converter('convert_from_extras'))

    schema.update(modifications)
    schema['resources'].update({
        'extract_job': [utils.default_to_none],
        'is_preview': [utils.default_to_false]
    })

    for key in schema.keys():
        if any([x in key for x in constants.REMOVED_FIELDS]):
            schema.pop(key, None)

    return schema

def update_package(context):
    package = context['package']
    resources = [
        r for r in package.resources_all if r.state == 'active'
    ]

    formats = []
    for r in resources:
        if ('datastore_active' in r.extras and r.extras['datastore_active']) or r.url_type == 'datastore':
            if r.format.lower() == 'csv':
                formats += constants.TABULAR_FORMATS
            elif r.format.lower() == 'geojson':
                formats += constants.GEOSPATIAL_FORMATS
        else:
            formats.append(r.format)

    formats = sorted(list(set([ f.upper() for f in formats ])))

    last_refreshed = [
        r.created if r.last_modified is None else r.last_modified for r in resources
    ]

    tk.get_action('package_patch')(context, {
        'id': package.id,
        'formats': ','.join(formats) if len(formats) > 0 else None,
        'last_refreshed': max(last_refreshed) if len(last_refreshed) > 0 else None
    })
