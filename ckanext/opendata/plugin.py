from . import api, schema, utils

import ckan.plugins as p
import ckan.plugins.toolkit as tk


class ExtendedAPIPlugin(p.SingletonPlugin):
    """
    # ==============================
    # IActions
    # ==============================
    These are custom api endpoints
    ex: hitting <ckan_url>/api/action/datastore_cache will
    trigger the api.datastore_cache function
    These can also be used with tk.get_action("datastore_cache"),
    for example, in this CKAN extension code
    """

    p.implements(p.IActions)

    def get_actions(self):
        return {
            "quality_show": api.get_quality_score,
            "search_packages": api.query_packages,
            "search_facet": api.query_facet,
            "datastore_cache": api.datastore_cache,
            "datastore_create": api.datastore_create_hook,
            "reindex_solr": api.reindex_solr
        }


class UpdateSchemaPlugin(p.SingletonPlugin):
    """
    # ===============
    # IValidators
    # ===============
    # Validates package / resource metadata attributes
    # These validators are referenced in our schema file
    """

    p.implements(p.IValidators)

    def get_validators(self):
        return {
            'validate_length': utils.validate_length,
            'choices_to_string': utils.choices_to_string,
            'string_to_choices': utils.string_to_choices,
            'default_to_today': utils.default_to_today,
            'default_to_false': utils.default_to_false,
            'default_to_none': utils.default_to_none
        }

    # ==============================
    # IResourceController
    # ==============================

    # Handles resources around their creation, update, and delete times
    # Specifically:
    #   makes sure resources that already exist arent created again
    #   creates the map preview for geojson data
    #   updates a package's formats and last_refreshed date based on changes
    #   to its resources

    p.implements(p.IResourceController, inherit=True)

    def before_create(self, context, resource):
        package = tk.get_action("package_show")(context, {
            "id": resource["package_id"]
        })

        # throw an error if we attempt to create 2 packages with the same name
        for idx, r in enumerate(package["resources"]):
            if r["name"] == resource["name"]:
                raise tk.ValidationError(
                    {
                        "constraints": [
                            "A resource with the name {name} already exists \
                            for this package".format(
                                name=r["name"]
                            )
                        ]
                    }
                )

        # auto assign a format, if the format isnt assigned yet
        if not ("format" in resource and resource["format"]):
            resource["format"] = resource["url"].split(".")[-1]

        resource["format"] = resource["format"].upper()

    def after_create(self, context, resource):
        schema.create_resource_views(context, resource)
        schema.update_package(context)

    def after_update(self, context, resource):
        schema.create_resource_views(context, resource)
        schema.update_package(context)

    def after_delete(self, context, resources):
        schema.update_package(context)


class ExtendedThemePlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)

    def update_config(self, config):
        tk.add_template_directory(config, 'catalog_templates')

    def get_helpers(self):
        return {
            "get_catalog": utils.get_catalog,
        }
