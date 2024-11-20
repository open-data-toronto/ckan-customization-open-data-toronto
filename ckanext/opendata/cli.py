import os

import click

from .clean_datastore_choices import SchemingMigration


@click.group()
def opendatatoronto():
    pass


@opendatatoronto.group()
def scheming_migration():
    pass


dry_run_option = click.option(
    "--not-dry-run",
    default=False,
    is_flag=True,
    help=(
        "If true, transactions wrapping this action will be aborted with an "
        "exception"
    ),
    type=bool,
)
log_directory_option = click.option(
    "--log-directory",
    default=os.path.dirname(__file__),
    help=("File path to a directory where the logs of changes will be written."),
    type=str,
)


@scheming_migration.command()
@click.option(
    "--field-names",
    default=None,
    required=True,
    help=(
        "Names of fields specified in scheming that will be audited (as a csv). If "
        "unspecified, all fields will be audited/migrated"
    ),
    type=str,
)
@dry_run_option
@log_directory_option
def apply(field_names, log_directory, not_dry_run):
    # (sorry): we want is_dry_run to be the default, but having a True default
    # for a CLI flag is misleading/impossible?
    is_dry_run = not not_dry_run
    fields = [name.strip() for name in field_names.split(",")]
    if not os.path.isdir(log_directory):
        raise ValueError(f"{log_directory} must be a valid directory")
    migration = SchemingMigration(log_directory)
    migration.apply(fields, is_dry_run)
    print(f"******Logs saved to {log_directory}")


@scheming_migration.command()
@dry_run_option
@log_directory_option
@click.argument(
    "csv_path",
    type=str,
)
def revert(not_dry_run, log_directory, csv_path):
    is_dry_run = not not_dry_run
    migration = SchemingMigration(log_directory)
    if not os.path.exists(csv_path):
        raise ValueError(f"Argument csv-path must exist and be a valid csv")
    migration.revert(csv_path=csv_path, dry_run=is_dry_run)
