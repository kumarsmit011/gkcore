# GKCORE

The REST API server of GNUKhata

- [API Docs](https://gnukhata.gitlab.io/gkcore/api-docs/)
- License: `APGPLv3`

# Development Setup

## Docker
- [docker](https://www.docker.com/) [Configure system to run docker as non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)
- [docker-compose](https://docs.docker.com/compose/)

- Create and move to project directory - `mkdir gnukhata && cd gnukhata`
- Build the project - `docker-compose --build up -d`
- To add configurations, add `--env_file path_to_configuration_file` to above command. Available configurations are listed [here](https://gitlab.com/gnukhata/gkcore/-/blob/devel/env.sample).
- To stop running GNUKhata, run - `docker-compose down`

## Manual Setup

Requirements:

- [python](https://www.python.org/) (v3.8 & above)
- postgresql
- python-poetry

Steps:

- Create postgresql database and user for the project.
- Clone the project to your system and move into project directory.
``` sh
git clone https://gitlab.com/gnukhata/gkcore.git
cd gkcore
```
- Add database name and user name to `.env` file, refer `env.template` for configuration options.
- Create project directory and start a python virtualenv.
- Install project dependancies.
``` sh
poetry install
```
- Add database tables and run migrations
``` sh
gkdb --init
gkdb --migrate
```
- Serve the project in production or development environment, default is production.
``` sh
gkserve [--development, --production]
```

> gkcore can be accessed at `http://localhost:6543`

> The API docs (swagger UI) can be accessed via `http://localhost:6543/docs/` from your web browser

## Windows 11

Requirements:

- [docker](https://docs.docker.com/desktop/setup/install/windows-install/)
- Follow the docker section for next steps.

### Troubleshooting:

- `docker inspect gkcore-db-1` **Run the command on cmd to check the IP address**
- `docker ps` **Run this command on cmd to check the status of the containers**

# Environment Variables:

- `GKCORE_DB_URL`: Provide a custom database URL

- `GKCORE_DISABLE_USER_REGISTRATION`: Default is `false`. Set to `true` to
    disable public user registration from login page. Note that admin users can
    still create and invite users to organisation.

- `GKCORE_DISABLE_ORG_REGISTRATION`: Default is `false`. Set to `true` to
    disable organisation registration.
    
- More configurations are listed [here](https://gitlab.com/gnukhata/gkcore/-/blob/devel/env.sample).

# After Installation

- When gkcore is installed on VPS, make sure to change the timezone to India with command `timedatectl set-timezone Asia/Kolkata` as organization logs pickup the default timezone.

# Contributions

Please refer [CONTRIBUTING.md](./CONTRIBUTING.md)

# Public instances

| API endpoint                 | Info                                                       |
| ---------------------------- | ---------------------------------------------------------- |
| https://api-dev.gnukhata.org | Hosted by GNUKhata team. this api is based on devel branch |

# Useful Links

- [Pyramid Framework](https://trypyramid.com/)
- [Open API Spec](https://swagger.io/docs/specification/about/)
- [Pyramid openAPI3](https://github.com/Pylons/pyramid_openapi3)

# Credits

- [Razorpay IFSC](https://github.com/razorpay/ifsc): IFSC validation server is used as a docker service
- pgadmin: Helps visualizing gnukhata's database locally
- GST Portal: For providing HSN/SAC codes spreadsheet
