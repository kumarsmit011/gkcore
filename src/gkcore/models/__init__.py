"""
Copyright (C) 2013, 2014, 2015, 2016 Digital Freedom Foundation
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
"""
import os

from dotenv import load_dotenv
from . import gkdb
from sqlalchemy.engine import create_engine

load_dotenv()


def generate_db_url():
    """ Generate database URL for engine creation. It will look for following
    environment variables, in absence, it will take the default values.

    GKCORE_DB_URL=
    GKCORE_DB_USER=
    GKCORE_DB_PASSWORD=
    GKCORE_DB_HOST=
    GKCORE_DB_PORT=
    GKCORE_DB_NAME=

    The use of dialect & driver are set to postgresql and psycopg2 until support for
    others are not tested or implemented.

    If GKCORE_DB_URL is given, it is used as database url, ignoring other variables.

    Link to SQL Alchemy documentation: https://docs.sqlalchemy.org/en/13/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg2
    """
    # if env variable GKCORE_DB_URL is set, Use it
    db_url = os.environ.get("GKCORE_DB_URL")

    if not db_url:
        # Setting default value using `get` method's `default` param won't work
        # if the variables are empty strings. So the `or` condition is added in the
        # following lines purposefully to handle fallback to default values in
        # such cases.
        db_name = os.environ.get("GKCORE_DB_NAME") or "gkdata"
        db_user = os.environ.get("GKCORE_DB_USER") or "gkadmin"
        db_password = os.environ.get("GKCORE_DB_PASSWORD") or "gkadmin"
        unix_sock_path = os.environ.get("UNIX_SOCKET_PATH")
        if unix_sock_path:
            db_url = (
                f"postgresql+psycopg2://{db_user}:{db_password}@/{db_name}?host={unix_sock_path}"
            )
        else:
            db_host = os.environ.get("GKCORE_DB_HOST") or "localhost"
            db_port = os.environ.get("GKCORE_DB_PORT") or 5432
            db_url = (
                f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            )

    return db_url

def get_engine():
    """Create engine that can be used to connect to the database.
    The echo parameter set to False means sql queries will not be printed to the terminal.
    Pool size is important to balance between database holding capacity in ram and speed.
    """
    return create_engine(generate_db_url(), echo=False, pool_size=15, max_overflow=100)

eng = get_engine()
