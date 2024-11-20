import csv
import io
import json
import logging
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Tuple

import ckan
import ckan.plugins.toolkit as tk
import sqlalchemy
from ckan.model import PackageExtra
from ckan.model.core import State
from ckanapi import LocalCKAN
from sqlalchemy.engine.base import Connection
from sqlalchemy.orm import Session

from ckanext.datastore.backend import DatastoreBackend
from ckanext.datastore.backend.postgres import identifier


class SchemingMigration:
    _log_columns = ["asctime", "name", "levelname", "message"]

    def __init__(self, log_directory: str):
        self._init_logger(log_directory)

    ####################################################################################
    #                              Helpers (static)                                    #
    ####################################################################################

    @staticmethod
    def get_field_by_name(field_name: str) -> Dict:
        dataset_fields = tk.h.scheming_dataset_schemas(expanded=True)["dataset"][
            "dataset_fields"
        ]
        field = next(
            field
            for field in dataset_fields
            if (
                field["field_name"] == field_name
                and field.get("choices_helper") == "scheming_datastore_choices"
            )
        )
        return field

    @staticmethod
    def get_datastore_resource_by_name(resource_name: str):
        # Following pattern from scheming_datastore_choices - anon user to prevent leakage
        # from tables:
        # "anon user must be able to read choices or this helper
        #  could be used to leak data from private datastore tables"
        # TODO ^is this required?
        lc = LocalCKAN(username="")
        return lc.action.datastore_search(
            resource_id=resource_name,
            # TODO paginate
            limit=99999999999999,
        )

    @staticmethod
    def _map_to_new_values(
        logger, current_val: str, updated_values: Dict[str, str]
    ) -> str:
        """
        Common formats (see unit tests for comprehensive set):
        {}
        {""}
        {"something here","something else here"}
        {something no quotes,"something with quotes"}
        {sometimes-spaces-between, sometimes-spaces-between}
        """
        # Add mappings for lower case so we can effectively ignore casing.
        updated_values_with_lower = {
            **updated_values,
            **{k.lower(): v for k, v in updated_values.items()},
        }
        # try to parse as json first, if fails, try parsing as python dict
        try:
            values = json.loads(current_val)
        except json.decoder.JSONDecodeError:
            cleaned = current_val.replace("{", "").replace("}", "")
            values = cleaned.split(",")
            values = [item.strip().replace('"', "") for item in values]
            values = [val for val in values if val]

        mapped_values = set()
        for value in values:
            options = {
                value,
                value.lower(),
                value.replace(" ", "_"),
                value.replace(" ", "_").lower(),
            }
            try:
                mapped_value = updated_values_with_lower[
                    next(opt for opt in options if opt in updated_values_with_lower)
                ]
                mapped_values.add(mapped_value)
            except StopIteration:
                logger.warning(
                    f"{value} not found/mapped in {updated_values_with_lower}, keeping "
                    f"as value {value}"
                )
                mapped_values.add(value)

        return json.dumps(sorted(mapped_values))

    @staticmethod
    def _csv_escape_values(values: List[str]) -> str:
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(values)
        return output.getvalue().strip()

    ####################################################################################
    #                              Private Methods                                     #
    ####################################################################################

    ###########
    # Logging #
    ###########

    def _init_logger(self, log_directory: str) -> None:
        self._logger = logging.Logger(__name__)
        format = [f"%({col})s" for col in self._log_columns]
        now = datetime.now().strftime("%Y-%m-%dT%H_%M_%S")

        log_name = f"{__name__}-{now}"
        log_path = os.path.join(log_directory, f"{log_name}.log")
        csv_path = os.path.join(log_directory, f"{log_name}.csv")

        # 3 Log outputs (handlers):
        # 1) one to std out (for human eyes)
        # 2) one to a log file (also for human eyes)
        # 3) one to a csv for machine-eyes, logging only the db operations.
        #    Kind of like a hacky CDC log that can be used to revert the operation.

        # human-eyes handlers:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_file_handler = logging.FileHandler(log_path)
        formatter = logging.Formatter(" - ".join(format))
        stdout_handler.setFormatter(formatter)
        stdout_file_handler.setFormatter(formatter)
        self._logger.addHandler(stdout_handler)
        self._logger.addHandler(stdout_file_handler)

        # CSV Logger
        self._csv_logger = logging.Logger(__name__)
        csv_path = Path(log_path).with_suffix(".csv")
        csv_handler = logging.FileHandler(csv_path)
        csv_formatter = logging.Formatter(
            self._csv_escape_values(format), "%Y-%m-%d %H:%M:%S"
        )
        # Filters only for logs tagged for csv
        csv_handler.setFormatter(csv_formatter)
        self._csv_logger.addHandler(csv_handler)

        with open(csv_path, "w") as file:
            file.write(
                ",".join(
                    self._log_columns[:-1]
                    + ["db", "table_name", "pk", "col_name", "old_value", "new_value"]
                )
                + "\n"
            )

        # Hard-code this, we want detailed trace of what happens written to a logfile
        self._logger.setLevel("DEBUG")
        self._csv_logger.setLevel("DEBUG")

    @contextmanager
    def _log_action(self, action_name: str, depth=1):
        prefix = "-" * (depth * 4)
        context = {"action_name": action_name, "prefix": prefix}
        start = datetime.now()
        self._logger.info("%(prefix)s BEGIN %(action_name)s", context)
        yield
        context["seconds"] = (datetime.now() - start).total_seconds()
        self._logger.info(
            "%(prefix)s COMPLETED %(action_name)s in %(seconds)ds",
            context,
        )

    def _log_pkg_extra_value_change(
        self, pkg_extra_id: str, old_value: str, new_value: str
    ):
        log_message = self._csv_escape_values(
            ["ckan", "package_extra", pkg_extra_id, "value", old_value, new_value]
        )
        self._csv_logger.info(log_message)

    def _log_datastore_choices_change(
        self, resource_id: str, _id: str, old_value: str, new_value: str
    ):
        log_message = self._csv_escape_values(
            ["datastore", resource_id, str(_id), "value", old_value, new_value]
        )
        self._csv_logger.info(log_message)

    ##########################
    # Transaction Management #
    ##########################

    @contextmanager
    def datastore_tx(self) -> Generator[Connection, None, None]:
        backend = DatastoreBackend.get_active_backend()
        engine = backend._get_write_engine()
        con = engine.connect()
        trans = con.begin()
        try:
            yield con
            trans.commit()
        except Exception:
            trans.rollback()
            raise
        finally:
            con.close()

    @contextmanager
    def _ckan_session(self):
        session = ckan.model.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    class _TransactionRollback(Exception):
        pass

    @contextmanager
    def _dry_run_tx(
        self, dry_run: bool
    ) -> Generator[Tuple[Connection, Session], None, None]:
        try:
            with self.datastore_tx() as datastore_con, self._ckan_session() as ckan_session:
                yield datastore_con, ckan_session
                if dry_run:
                    raise self._TransactionRollback()
        except self._TransactionRollback:
            self._logger.info("Changes rolled back for dry_run=True")

    ##############
    # DB Actions #
    ##############

    def _apply_one_field(
        self, ckan_session: Session, datastore_con: Connection, field_name: str
    ):
        field = self.get_field_by_name(field_name)
        resource_name = field["datastore_choices_resource"]
        datastore_search_result = self.get_datastore_resource_by_name(resource_name)
        datastore_records = datastore_search_result["records"]
        resource_id = datastore_search_result["resource_id"]
        self._logger.info("Records pre-change:")
        self._logger.info(" ".join(str(val) for val in datastore_records))

        value_col = field["datastore_choices_columns"]["value"]
        label_col = field["datastore_choices_columns"]["label"]
        package_extra_updated_values = {
            item["value"]: item["label"] for item in datastore_records
        }

        # perform action on datastore db
        with self._log_action(
            f"Update datastore choices {field_name} ({resource_id})",
            depth=2,
        ):
            self._update_datastore_choice_value_to_label(
                datastore_con,
                resource_id,
                value_col,
                label_col,
            )

        # log changes (so we have record of what changed)
        for record in datastore_records:
            if record["value"] != record["label"]:
                value, label, _id = record["value"], record["label"], record["_id"]
                self._log_datastore_choices_change(resource_id, _id, value, label)
                self._logger.info(
                    "Datastore choice for %(resource_name)s changed from %(value)s to %(label)s",
                    {"resource_name": resource_name, "value": value, "label": label},
                )

        # perform action on ckan db
        with self._log_action(
            f"Correct PackageExtra records for {field_name}",
            depth=2,
        ):
            self._repair_package_extra_multi_choices(
                ckan_session,
                resource_name,
                package_extra_updated_values,
            )

    def _update_datastore_choice_value_to_label(
        self, datastore_con, resource_id, value_col, label_col
    ):
        sql = sqlalchemy.text(
            """update {0} set {1}={2}""".format(
                identifier(resource_id),
                identifier(value_col),
                identifier(label_col),
            )
        )
        self._logger.info("Executing against datastore db: %(sql)s", {"sql": str(sql)})
        datastore_con.execute(sql)

    def _repair_package_extra_multi_choices(
        self, session, key: str, updated_values: Dict[str, str]
    ):
        extras = (
            session.query(PackageExtra)
            .filter(PackageExtra.key == key, PackageExtra.state == State.ACTIVE)
            .all()
        )
        for extra in extras:
            new_value = self._map_to_new_values(
                self._logger, extra.value, updated_values
            )
            if new_value != extra.value:
                self._logger.info(
                    (
                        "PackagExtra(id=%(id)s) change value from %(value)s to "
                        "%(new_value)s"
                    ),
                    {"id": extra.id, "value": extra.value, "new_value": new_value},
                )
                self._log_pkg_extra_value_change(extra.id, extra.value, new_value)
                extra.value = new_value
            else:
                self._logger.info(
                    "PackagExtra(id=%(id)s) keeping same value %(value)s",
                    {"id": extra.id, "value": extra.value},
                )

    def _update_value(
        self,
        con: Connection,
        table_name: str,
        col_name: str,
        pk: str,
        pk_colname: str,
        value,
    ):
        table_name = identifier(table_name)
        column = identifier(col_name)
        pk_colname = identifier(pk_colname)

        query = sqlalchemy.text(
            f"update {table_name} SET {column}=:value where {pk_colname}=:pk"
        )
        self._logger.info(f"Executing against {con}: {query} {value, pk}")
        con.execute(query, {"value": value, "pk": pk})

    ####################################################################################
    #                                  Public APIs                                     #
    ####################################################################################

    def apply(self, fields: List[str], dry_run: bool):
        with self._dry_run_tx(dry_run=dry_run) as (datastore_con, ckan_session):
            for field_name in fields:
                with self._log_action(f"Applying changes to field {field_name}"):
                    self._apply_one_field(ckan_session, datastore_con, field_name)

    def revert(self, csv_path: str, dry_run: bool):
        from csv import DictReader

        with open(csv_path, "r") as file:
            reader = DictReader(file)
            changes = list(reader)

        datastore_items = [change for change in changes if change["db"] == "datastore"]
        ckan_items = [change for change in changes if change["db"] == "ckan"]

        with self._dry_run_tx(dry_run=dry_run) as (datastore_con, ckan_session):

            # Datastore choices tables
            with self._log_action(f"Reverting {len(datastore_items)} datastore items"):
                for item in datastore_items:
                    self._update_value(
                        con=datastore_con,
                        table_name=item["table_name"],
                        col_name=item["col_name"],
                        pk=item["pk"],
                        pk_colname="_id",
                        value=item["old_value"],
                    )

            # PackageExtra table
            with self._log_action(f"Reverting {len(ckan_items)} ckan items"):
                for item in ckan_items:
                    self._update_value(
                        con=ckan_session,
                        table_name=item["table_name"],
                        col_name=item["col_name"],
                        pk=item["pk"],
                        pk_colname="id",
                        value=item["old_value"],
                    )
