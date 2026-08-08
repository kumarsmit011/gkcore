"""
Copyright (C) 2013, 2014, 2015, 2016 Digital Freedom Foundation
Copyright (C) 2017, 2018, 2019, 2020 Digital Freedom Foundation & Accion Labs 
  This file is part of GNUKhata:A modular,robust and Free Accounting System.

  GNUKhata is Free Software; you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as
  published by the Free Software Foundation; either version 3 of
  the License, or (at your option) any later version.

  GNUKhata is distributed in the hope that it will be useful, but
  WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public
  License along with GNUKhata (COPYING); if not, write to the
  Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
  Boston, MA  02110-1301  USA59 Temple Place, Suite 330,


Contributors:
"Krishnakant Mane" <kk@gmail.com>
"Ishan Masdekar " <imasdekar@dff.org.in>
"Navin Karkera" <navin@dff.org.in>
"Prajkta Patkar"<prajkta.patkar007@gmail.com>
"""

# this module contains the functions and objects needed for database objects configuration.
# Metadata is one such object which helps to get all database related info.
# inspect is another functions from alchemy which helps to find details info on tables or columns.

from sqlalchemy.dialects.postgresql.base import PGInspector
import json
from pyramid.request import Request
from sqlalchemy import inspect
from gkcore.models.gkdb import metadata
from gkcore.utils import gk_log
from gkcore import eng


def does_foreignkey_exist(eng, table_name, constraint_name):
    # Inspect the database to check for the constraint
    inspector = inspect(eng)
    constraints = inspector.get_foreign_keys(table_name)
    # return true if the constraint already exists
    return any(constraint['name'] == constraint_name for constraint in constraints)

def does_check_constraint_exist(eng, table_name, constraint_name):
    # Inspect the database to check for the constraint
    inspector = inspect(eng)
    constraints = inspector.get_check_constraints(table_name)
    # return true if the constraint already exists
    return any(constraint['name'] == constraint_name for constraint in constraints)

def does_unique_constraint_exist(eng, table_name, constraint_name):
    # Inspect the database to check for the constraint
    inspector = inspect(eng)
    constraints = inspector.get_unique_constraints(table_name)
    # return true if the constraint already exists
    return any(constraint['name'] == constraint_name for constraint in constraints)


def does_primarykey_exist(eng, table_name, constraint_name):
    # Inspect the database to check for the constraint
    inspector = inspect(eng)
    constraint = inspector.get_pk_constraint(table_name)
    # return true if the constraint already exists
    return constraint['name'] == constraint_name


def inventoryMigration(con, eng):
    metadata.create_all(eng)
    con.execute(
        "alter table categorysubcategories add  foreign key (subcategoryof) references categorysubcategories(categorycode)"
    )
    con.execute(
        "alter table unitofmeasurement add  foreign key (subunitof) references unitofmeasurement(uomid)"
    )
    con.execute("alter table organisation add column invflag Integer default 0 ")
    con.execute("alter table vouchers add column invid Integer")
    con.execute(
        "alter table vouchers add foreign key (invid) references invoice(invid)"
    )
    try:
        con.execute("select themename from users")
    except:
        con.execute("alter table users add column themename text default 'Default'")
    return 0


def addFields(con, eng):
    metadata.create_all(eng)
    try:
        con.execute("select noofpackages,modeoftransport from delchal")
        con.execute("select recieveddate from transfernote")
    except:
        con.execute("alter table transfernote add recieveddate date")
        con.execute("alter table delchal add noofpackages int")
        con.execute("alter table delchal add modeoftransport text")
    return 0


def columnExists(tableName, columnName):
    """
    purpose:
    Checkes weather the column mentiond is alredy present in the given table.
    description:
    Given the table and the name of the column, this functions checks if that column exists.
    It uses the inspect function to do so.
    The function traverces through the list of columns and checks if the name exists.
    Returns True if the column exists or False otherwise.
    """
    gkInspect = PGInspector(eng)
    cols = gkInspect.get_columns(tableName)
    for col in cols:
        if col["name"] == columnName:
            return True
    return False


def uniqueConstraintExists(tableName, constraints):
    gkInspect = PGInspector(eng)
    cols = map(lambda x: x["column_names"], gkInspect.get_unique_constraints(tableName))
    exists = True
    col_names = list(cols)
    for constraint in constraints:
        if not constraint in col_names[0]:
            exists = False
            break
        else:
            print(constraint)
    return exists


def columnTypeMatches(tableName, columnName, columnType):
    gkInspect = PGInspector(eng)
    cols = gkInspect.get_columns(tableName)
    for col in cols:
        if col["name"] in columnName:
            if type(col["type"]) is columnType:
                return True
    return False


def tableExists(tblName):
    """
    purpose:
    Finds out weather the given table exists in the database.
    Function uses inspect object for postgresql.
    """
    gkInspect = PGInspector(eng)
    tblList = gkInspect.get_table_names()
    return tblName in tblList


def getOnDelete(tblName, keyName):
    """
    purpose:
    Returns the value of ondelete option for a foreign key in a table.
    Accepts names of table and the foreign key as params.
    It fetches all foreign keys and then loops through them.
    On finding the matching foreign key, its value for ondelete option is returned.
    """
    onDelete = False
    gkInspect = PGInspector(eng)
    fkeys = gkInspect.get_foreign_keys(tblName)
    for fkey in fkeys:
        if fkey["name"] == keyName:
            onDelete = fkey["options"]["ondelete"]
    return onDelete


def gk_api(
    url: str,
    header: object,
    request: object,
    method: str = "GET",
    body: dict = None,
):
    """Call's gkcore api internally

    If success, returns result object, else raises Exception.

    **params**

    `url` = api url (eg: '/state')\n
    `header` = url headers\n
    `request` = request object\n
    `method` = valid REST method, Allowed values: `GET`, `POST`. Default is `GET`\n
    `body` = request body as dict
    """
    try:
        subreq = Request.blank(url, headers=header)

        if method == "POST":
            Request.method = "POST"
            Request.json_body = body

        result = json.loads(request.invoke_subrequest(subreq).text)
        return result
    except Exception as e:
        gk_log(__name__).warn(f"gk_api(): {e}")
        raise
