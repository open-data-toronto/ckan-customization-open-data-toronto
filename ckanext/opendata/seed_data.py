"""Seed data and seeding helpers used by the `seed` CLI command for local development."""

import click
from enum import Enum


# ---------------------------------------------------------------------------
# Lookup enums for scheming_datastore_choices fields.
# Values are sourced from the Metadata Catalog:
# https://open.toronto.ca/dataset/metadata-catalog/
# ---------------------------------------------------------------------------

class DatasetCategory(Enum):
    Document = "Document"
    Map = "Map"
    Table = "Table"
    Website = "Website"


class RefreshRate(Enum):
    Daily = "Daily"
    Weekly = "Weekly"
    Monthly = "Monthly"
    Quarterly = "Quarterly"
    Semi_annually = "Semi-annually"
    Annually = "Annually"
    Real_time = "Real-time"
    As_available = "As available"
    Will_not_be_Refreshed = "Will not be Refreshed"
    Bi_weekly = "Bi-weekly"


class OwnerDivision(Enum):
    Shelter_Support_Housing_Administration = "Shelter, Support & Housing Administration"
    Toronto_311 = "311 Toronto"
    City_Planning = "City Planning"
    Information_Technology = "Information & Technology"
    Toronto_Office_of_Recovery_and_Rebuild = "Toronto Office of Recovery and Rebuild"
    Toronto_Public_Health = "Toronto Public Health"
    Toronto_Paramedic_Services = "Toronto Paramedic Services"
    Environment_Energy = "Environment & Energy"
    Municipal_Licensing_Standards = "Municipal Licensing & Standards"
    City_Clerks_Office = "City Clerk's Office"
    Transportation_Services = "Transportation Services"
    Toronto_Water = "Toronto Water"
    Toronto_Police_Services = "Toronto Police Services"
    Toronto_Parking_Authority = "Toronto Parking Authority"
    Engineering_Construction_Services = "Engineering & Construction Services"
    Financial_Planning = "Financial Planning"
    Toronto_Building = "Toronto Building"
    Economic_Development_Culture = "Economic Development & Culture"
    Purchasing_Materials_Management = "Purchasing & Materials Management"
    Strategic_Corporate_Policy = "Strategic & Corporate Policy"
    Childrens_Services = "Children's Services"
    Revenue_Services = "Revenue Services"
    City_Managers_Office = "City Manager's Office"
    Social_Development_Finance_Administration = "Social Development, Finance & Administration"
    Accounting_Services = "Accounting Services"
    People_Equity = "People & Equity"
    Court_Services = "Court Services"
    Corporate_Finance = "Corporate Finance"
    Fire_Services = "Fire Services"
    Parks_Forestry_Recreation = "Parks, Forestry & Recreation"
    Equity_Diversity_Human_Rights = "Equity, Diversity & Human Rights"
    Employment_Social_Services = "Employment & Social Services"
    Human_Resources = "Human Resources"
    Toronto_Transit_Commission = "Toronto Transit Commission"
    Lobbyist_Registrar = "Lobbyist Registrar"
    Seniors_Services_Long_Term_Care = "Seniors Services & Long-Term Care"
    Toronto_Public_Library = "Toronto Public Library"
    Solid_Waste_Management_Services = "Solid Waste Management Services"
    Facilities_Management = "Facilities Management"
    Toronto_Catholic_District_School_Board = "Toronto Catholic District School Board"
    Fleet_Services = "Fleet Services"
    Housing_Secretariat = "Housing Secretariat"
    Corporate_Real_Estate_Management = "Corporate Real Estate Management"
    Toronto_Shelter_Support_Services = "Toronto Shelter & Support Services"
    Environment_Climate = "Environment & Climate"
    Policy_Planning_Finance_Administration = "Policy, Planning, Finance & Administration"
    Development_Review = "Development Review"


class CivicIssues(Enum):
    Affordable_housing = "Affordable housing"
    Climate_change = "Climate change"
    Fiscal_responsibility = "Fiscal responsibility"
    Mobility = "Mobility"
    Poverty_reduction = "Poverty reduction"


class Formats(Enum):
    CSV = "CSV"
    XLSX = "XLSX"
    SHP = "SHP"
    XML = "XML"
    JSON = "JSON"
    GEOJSON = "GEOJSON"
    GPKG = "GPKG"
    XLS = "XLS"
    ZIP = "ZIP"
    WEB = "WEB"
    DOCX = "DOCX"
    PDF = "PDF"
    TXT = "TXT"
    XSD = "XSD"
    DOC = "DOC"
    GZ = "GZ"
    KML = "KML"
    RAR = "RAR"
    SAV = "SAV"
    XLSM = "XLSM"
    PNG = "PNG"


class Topics(Enum):
    City_government = "City government"
    Locations_and_mapping = "Locations and mapping"
    Community_services = "Community services"
    Transportation = "Transportation"
    Public_safety = "Public safety"
    Health = "Health"
    Finance = "Finance"
    Culture_and_tourism = "Culture and tourism"
    Environment = "Environment"
    Business = "Business"
    Parks_and_recreation = "Parks and recreation"
    Permits_and_licenses = "Permits and licenses"
    Water = "Water"
    Garbage_and_recycling = "Garbage and recycling"
    Development_and_infrastructure = "Development and infrastructure"


def _choices(enum_cls) -> list:
    return [{"value": m.value, "label": m.value} for m in enum_cls]


LOOKUP_TABLES = {
    "dataset_category": _choices(DatasetCategory),
    "refresh_rate": _choices(RefreshRate),
    "owner_division": _choices(OwnerDivision),
    "civic_issues": _choices(CivicIssues),
    "formats": _choices(Formats),
    "topics": _choices(Topics),
}


INTAKE_STATUSES_SAMPLE = [
    {
        "status": "Open",
        "definition": "A new inquiry has been opened.",
        "colour": "#4A90D9",
        "public_name": "New Inquiry",
        "category": "new",
    },
    {
        "status": "In Progress",
        "definition": "Open Data is actively working on this ticket.",
        "colour": "#F5A623",
        "public_name": "In Progress",
        "category": None,
    },
    {
        "status": "Under Review",
        "definition": "The request is being reviewed by Open Data staff.",
        "colour": "#9B59B6",
        "public_name": "Under Review",
        "category": None,
    },
    {
        "status": "WIP",
        "definition": "Work is in progress on this dataset.",
        "colour": "#E67E22",
        "public_name": "Work In Progress",
        "category": None,
    },
    {
        "status": "Published",
        "definition": "The dataset has been published to the Open Data Portal.",
        "colour": "#27AE60",
        "public_name": "Published",
        "category": "done",
    },
    {
        "status": "Closed",
        "definition": "This ticket has been closed without publication.",
        "colour": "#7F8C8D",
        "public_name": "Closed",
        "category": "done",
    },
    {
        "status": "Retired",
        "definition": "This dataset has been retired from the portal.",
        "colour": "#95A5A6",
        "public_name": "Retired",
        "category": "done",
    },
]

INTAKE_RECORDS_SAMPLE = [
    # DIA-1: open inquiry, two status transitions (no linked ticket)
    {
        "Ticket Id": "DIA-1",
        "Ticket Name": "I'd like to request a new dataset",
        "Inquiry Source": "Public",
        "Division": "Information & Technology",
        "Public Description": "A request to publish a new sample dataset.",
        "Request Type": "Open Data Inquiry",
        "Created": "2024-01-15T09:00:00",
        "First Response": "2024-01-16T10:00:00",
        "Ticket Resolved?": "false",
        "From Status": None,
        "To Status": "Open",
        "Status Timestamp": "2024-01-15T09:00:00",
        "Linked Ticket Id": "",
    },
    {
        "Ticket Id": "DIA-1",
        "Ticket Name": "I'd like to request a new dataset",
        "Inquiry Source": "Public",
        "Division": "Information & Technology",
        "Public Description": "A request to publish a new sample dataset.",
        "Request Type": "Open Data Inquiry",
        "Created": "2024-01-15T09:00:00",
        "First Response": "2024-01-16T10:00:00",
        "Ticket Resolved?": "false",
        "From Status": "Open",
        "To Status": "In Progress",
        "Status Timestamp": "2024-01-20T14:00:00",
        "Linked Ticket Id": "",
    },
    # DIA-2: publish ticket linked to inquiry DIA-3
    {
        "Ticket Id": "DIA-2",
        "Ticket Name": "Publish New Dataset: Sample Data",
        "Inquiry Source": "Internal",
        "Division": "Information & Technology",
        "Public Description": "Publishing sample dataset to the Open Data Portal.",
        "Request Type": "Publish a New Open Dataset Page",
        "Created": "2024-02-01T09:00:00",
        "First Response": "2024-02-01T11:00:00",
        "Ticket Resolved?": "false",
        "From Status": None,
        "To Status": "Open",
        "Status Timestamp": "2024-02-01T09:00:00",
        "Linked Ticket Id": "DIA-3",
    },
    {
        "Ticket Id": "DIA-2",
        "Ticket Name": "Publish New Dataset: Sample Data",
        "Inquiry Source": "Internal",
        "Division": "Information & Technology",
        "Public Description": "Publishing sample dataset to the Open Data Portal.",
        "Request Type": "Publish a New Open Dataset Page",
        "Created": "2024-02-01T09:00:00",
        "First Response": "2024-02-01T11:00:00",
        "Ticket Resolved?": "false",
        "From Status": "Open",
        "To Status": "WIP",
        "Status Timestamp": "2024-02-05T10:00:00",
        "Linked Ticket Id": "DIA-3",
    },
    # DIA-3: inquiry linked to publish ticket DIA-2
    {
        "Ticket Id": "DIA-3",
        "Ticket Name": "I'd like to request a new sample dataset",
        "Inquiry Source": "Public",
        "Division": "Information & Technology",
        "Public Description": "An inquiry that led to the publication of a new dataset.",
        "Request Type": "Open Data Inquiry",
        "Created": "2024-01-10T09:00:00",
        "First Response": "2024-01-11T09:00:00",
        "Ticket Resolved?": "false",
        "From Status": None,
        "To Status": "Open",
        "Status Timestamp": "2024-01-10T09:00:00",
        "Linked Ticket Id": "DIA-2",
    },
    # DIA-4: resolved update ticket (two transitions, ends Published)
    {
        "Ticket Id": "DIA-4",
        "Ticket Name": "Update Existing Dataset: Traffic Volumes",
        "Inquiry Source": "Internal",
        "Division": "Transportation Services",
        "Public Description": "Annual update to the traffic volumes dataset.",
        "Request Type": "I'd like to update an existing dataset or page",
        "Created": "2023-11-01T09:00:00",
        "First Response": "2023-11-02T09:00:00",
        "Ticket Resolved?": "true",
        "From Status": None,
        "To Status": "Open",
        "Status Timestamp": "2023-11-01T09:00:00",
        "Linked Ticket Id": "",
    },
    {
        "Ticket Id": "DIA-4",
        "Ticket Name": "Update Existing Dataset: Traffic Volumes",
        "Inquiry Source": "Internal",
        "Division": "Transportation Services",
        "Public Description": "Annual update to the traffic volumes dataset.",
        "Request Type": "I'd like to update an existing dataset or page",
        "Created": "2023-11-01T09:00:00",
        "First Response": "2023-11-02T09:00:00",
        "Ticket Resolved?": "true",
        "From Status": "Open",
        "To Status": "Published",
        "Status Timestamp": "2023-12-15T09:00:00",
        "Linked Ticket Id": "",
    },
]


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------

def seed_org(lc):
    click.echo("Creating default organisation...")
    try:
        org = lc.action.organization_show(id="city-of-toronto")
        click.echo("  Already exists, reusing.")
    except Exception:
        org = lc.action.organization_create(
            name="city-of-toronto",
            title="City of Toronto",
        )
        click.echo(f"  Created: {org['id']}")
    return org


def seed_lookup_tables(lc, model, uuid_module, org_id):
    """Create the 'metadata-catalog' package and populate lookup tables.

    Uses the model layer directly to bypass scheming validators — the lookup
    data doesn't exist yet when this runs (classic circular dependency).
    datastore_create is then called normally so it registers the aliases that
    scheming_datastore_choices resolves at validation time.
    """
    click.echo("Creating reference data package...")
    choices_pkg_obj = model.Package.get("metadata-catalog")
    if choices_pkg_obj:
        choices_pkg_id = choices_pkg_obj.id
        click.echo("  Already exists, reusing.")
    else:
        choices_pkg_id = str(uuid_module.uuid4())
        choices_pkg_obj = model.Package(
            id=choices_pkg_id,
            name="metadata-catalog",
            title="Metadata Catalog",
            notes="List of the tags that the Toronto Open Data Portal will use to categorize and search its datasets",
            type="dataset",
            state="active",
            private=False,
            owner_org=org_id,
        )
        model.Session.add(choices_pkg_obj)
        model.Session.add(model.Member(
            table_id=choices_pkg_id,
            table_name="package",
            group_id=org_id,
            state="active",
            capacity="public",
        ))
        model.Session.commit()
        click.echo(f"  Created: {choices_pkg_id}")

    click.echo("Seeding lookup tables...")
    for i, (table_name, records) in enumerate(LOOKUP_TABLES.items()):
        resource_label = table_name.replace("_", " ").title()
        existing_resource = (
            model.Session.query(model.Resource)
            .filter_by(package_id=choices_pkg_id, name=resource_label)
            .first()
        )
        if existing_resource:
            resource_id = existing_resource.id
            click.echo(f"  Resource already exists: {resource_label}")
        else:
            resource_id = str(uuid_module.uuid4())
            res = model.Resource(
                package_id=choices_pkg_id,
                name=resource_label,
                url="http://placeholder",
                format="CSV",
            )
            res.id = resource_id
            res.state = "active"
            res.position = i
            model.Session.add(res)
            model.Session.commit()
            click.echo(f"  Created resource: {resource_label}")

        try:
            lc.action.datastore_create(
                resource_id=resource_id,
                aliases=[table_name],
                fields=[
                    {"id": "value", "type": "text"},
                    {"id": "label", "type": "text"},
                ],
                records=records,
                primary_key=["value"],
                force=True,
                do_not_cache=True,
            )
            click.echo(f"  Datastore populated: {table_name}")
        except Exception as exc:
            click.echo(f"  Datastore already exists for {table_name} ({exc}), skipping.")


def seed_sample_dataset(lc, org_id):
    """Create 'sample-dataset' with a small datastore resource.

    Lookup tables must already exist so scheming validators can resolve
    choices for dataset_category, refresh_rate, and owner_division.
    """
    click.echo("Seeding sample dataset...")
    try:
        lc.action.package_show(id="sample-dataset")
        click.echo("  Sample dataset already exists, skipping.")
        return
    except Exception:
        pass

    sample_pkg = lc.action.package_create(
        name="sample-dataset",
        title="Sample Dataset",
        notes="A sample dataset created during local development seeding.",
        dataset_category="Table",
        refresh_rate="Daily",
        owner_division="Information & Technology",
        url="https://open.toronto.ca",
        information_url="https://open.toronto.ca",
        owner_org=org_id,
        private=False,
    )
    click.echo(f"  Created sample dataset: {sample_pkg['id']}")

    resource = lc.action.resource_create(
        package_id=sample_pkg["id"],
        name="sample-data",
        format="CSV",
        url="http://placeholder",
    )
    click.echo(f"  Created resource: {resource['id']}")

    lc.action.datastore_create(
        resource_id=resource["id"],
        fields=[
            {"id": "id", "type": "int"},
            {"id": "name", "type": "text"},
            {"id": "value", "type": "numeric"},
        ],
        records=[
            {"id": 1, "name": "alpha", "value": 1.1},
            {"id": 2, "name": "beta", "value": 2.2},
            {"id": 3, "name": "gamma", "value": 3.3},
        ],
        primary_key=["id"],
        force=True,
        do_not_cache=True,
    )
    click.echo("  Populated sample datastore.")


def seed_intake_dataset(lc, model, uuid_module, org_id):
    """Create the 'open-data-intake' package with intake records and statuses.

    Uses the model layer directly (same reason as seed_lookup_tables) to
    avoid circular validation dependencies.
    """
    click.echo("Seeding open-data-intake dataset...")

    intake_pkg_obj = model.Package.get("open-data-intake")
    if intake_pkg_obj:
        intake_pkg_id = intake_pkg_obj.id
        click.echo("  open-data-intake package already exists, reusing.")
    else:
        intake_pkg_id = str(uuid_module.uuid4())
        intake_pkg_obj = model.Package(
            id=intake_pkg_id,
            name="open-data-intake",
            title="Toronto Open Data Intake",
            notes="This dataset displays the Open Data intake queue.",
            type="dataset",
            state="active",
            private=False,
            owner_org=org_id,
        )
        model.Session.add(intake_pkg_obj)
        model.Session.add(model.Member(
            table_id=intake_pkg_id,
            table_name="package",
            group_id=org_id,
            state="active",
            capacity="public",
        ))
        model.Session.commit()
        click.echo(f"  Created: {intake_pkg_id}")

    for i, (resource_name, fields, records, primary_key) in enumerate([
        (
            "Open Data Intake Records",
            [
                {"id": "Ticket Id", "type": "text"},
                {"id": "Ticket Name", "type": "text"},
                {"id": "Inquiry Source", "type": "text"},
                {"id": "Division", "type": "text"},
                {"id": "Public Description", "type": "text"},
                {"id": "Request Type", "type": "text"},
                {"id": "Created", "type": "text"},
                {"id": "First Response", "type": "text"},
                {"id": "Ticket Resolved?", "type": "text"},
                {"id": "From Status", "type": "text"},
                {"id": "To Status", "type": "text"},
                {"id": "Status Timestamp", "type": "text"},
                {"id": "Linked Ticket Id", "type": "text"},
            ],
            INTAKE_RECORDS_SAMPLE,
            [],
        ),
        (
            "statuses",
            [
                {"id": "status", "type": "text"},
                {"id": "definition", "type": "text"},
                {"id": "colour", "type": "text"},
                {"id": "public_name", "type": "text"},
                {"id": "category", "type": "text"},
            ],
            INTAKE_STATUSES_SAMPLE,
            ["status"],
        ),
    ]):
        existing_resource = (
            model.Session.query(model.Resource)
            .filter_by(package_id=intake_pkg_id, name=resource_name)
            .first()
        )
        if existing_resource:
            resource_id = existing_resource.id
            click.echo(f"  Resource already exists: {resource_name}")
        else:
            resource_id = str(uuid_module.uuid4())
            res = model.Resource(
                package_id=intake_pkg_id,
                name=resource_name,
                url="http://placeholder",
                format="CSV",
            )
            res.id = resource_id
            res.state = "active"
            res.position = i
            model.Session.add(res)
            model.Session.commit()
            click.echo(f"  Created resource: {resource_name}")

        try:
            lc.action.datastore_create(
                resource_id=resource_id,
                fields=fields,
                records=records,
                primary_key=primary_key,
                force=True,
                do_not_cache=True,
            )
            click.echo(f"  Datastore populated: {resource_name}")
        except Exception as exc:
            click.echo(f"  Datastore already exists for {resource_name} ({exc}), skipping.")
