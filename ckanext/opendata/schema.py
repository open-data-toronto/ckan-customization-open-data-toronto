import utils

def modify_schema(schema, show=False):
    for key in schema.keys():
        if any([x in key for x in constants.REMOVED_FIELDS]):
            schema.pop(key, None)

    modifications = utils.get_package_schema()

    for key, value in modifications.items():
        if show:
            modifications[key].insert(
                0, tk.get_converter('convert_from_extras')
            )
        else:
            modifications[key].insert(
                1, tk.get_converter('convert_to_extras')
            )

    schema.update(modifications)

    schema['resources'].update( utils.get_resource_schema() )

    return schema

def update_package(context):
    package = context['package']
    resources = [
        r for r in package.resources_all if r.state == 'active'
    ]

    formats = []
    for r in resources:
        if ('datastore_active' in r.extras and r.extras['datastore_active']) \
            or r.url_type == 'datastore':

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
