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
"Prajkta Patkar"<prajakta@dff.org.in>


Main entry point:
This package initializer module is run when the application is served.
The module contains enum dict containing all gnukahta success and failure messages.
It also contains all the routes which are connected to respective resources.
To trace the link of the routes we look at the name of a route and then see where it appeares in any of the @view_defaults or @view_config decorator of any resource.
This module also scanns for the secret from the database which is then used for jwt authentication.
"""

import os
from pyramid.config import Configurator
from wsgicors import CORS
from gkcore.data.enum import STATUS_CODES as enumdict
from dotenv import load_dotenv
from gkcore.models import eng

# Load environment variables from the .env file
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main(global_config, **settings):
    config = Configurator(settings=settings)
    if os.environ.get("SHOW_SWAGGER_UI", "true") != "false":
        config.include(".swagger")
        # include the pyramid-openapi3 plugin config
        # link: https://github.com/Pylons/pyramid_openapi3
    config.include('.security')
    config.include('.routes')
    if settings.get('development'): # Use only when it is development mode.
        config.include('.logging')
    config.include('.renderers')
    config.scan()

    return CORS(
        config.make_wsgi_app(), headers="*", methods="*", maxage="180", origin="*"
    )
