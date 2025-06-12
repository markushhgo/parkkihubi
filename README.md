[![Build status](https://travis-ci.org/City-of-Helsinki/parkkihubi.svg?branch=master)](https://travis-ci.org/City-of-Helsinki/parkkihubi)
[![codecov](https://codecov.io/gh/City-of-Helsinki/parkkihubi/branch/master/graph/badge.svg)](https://codecov.io/gh/City-of-Helsinki/parkkihubi)
[![Requirements](https://requires.io/github/City-of-Helsinki/parkkihubi/requirements.svg?branch=master)](https://requires.io/github/City-of-Helsinki/parkkihubi/requirements/?branch=master)

# Parking hub

Django-based REST API for processing parking data.

## Requirements

* Ubuntu 22.04
* Python 3.10
* PostgreSQL 14 + PostGIS 3.4

## Preferred usage with Visual Studio Code

Install Remote Containers support in Visual Studio Code with these instructions:

* https://code.visualstudio.com/docs/remote/remote-overview
* https://code.visualstudio.com/docs/remote/containers

After that this should be easy, if all that magic works:

* Open the project folder in Visual Studio Code
* It asks to reopen the folder in remote container
* Accept
* Wait a while for it to automatically build the environment for you

You are free to change the included VSCode settings locally for yourself but it is
expected that you produce code which pass linters defined in the preferred settings.

In the debug panel you can run following with debugger enabled:

* Django runserver in hot reload mode
* Django shell
* Django migrations
* Generate new Django migrations for all Django apps

Happy hacking :)

## Usage with docker-compose

Development environment can also be run directtly with docker-compose. For this to
work `local_settings.py` -file needs to be created. Easiest way to do this is to copy
template file to proper location.

```
cp -n local_settings.py.tpl_dev local_settings.py
```

After this you can start docker compose environment

```
docker-compose --compatibility up
```

To run commands inside docker environment, execute shell process in `runserver`
container. There are at least zsh and bash shells available.

```
docker-compose exec runserver /bin/zsh
# or with bash
docker-compose exec runserver /bin/bash
```

Vistual environment should be active by default in both shells. After this you can
run migrations, collecstatic and other management commands inside container in
`~/bew` -directory.

### Possible problems with environment

This container uses Python venv virtual environment. Command called from host system
needs to use python executables from venv path ie. pytest needs to be run with fill
path.

```
docker-compose exec runserver /home/bew/.venv/bin/pytest
```

This container has default user `bew` that expects your uid and git to be 1000 on
host system to access files in docker volumes. In Ubuntu uid and gid 1000 is default
for first user account created on system. This may lead to file permission problems.

To fix this, there is docker compose file `docker-compose-root.yml` that can be used
instead of the default one. Because commands are run with root acces inside the
container this may create files with root permissions on the host system.

### Python requirements

Use `pip-tools` to install and maintain installed dependencies. This also needs
build essentials and required development libraries installed.

    sudo apt-get install build-essential libpq-dev
    pip install pip-tools

Use pip-compile to update the `requirements*.txt` files.

    pip-compile requirements.in
    pip-compile requirements-dev.in

### Django configuration

Environment variables are used to customize base configuration in
`parkkihubi/settings.py`. If you wish to override any settings, you can place
them in a local `.env` file which will automatically be sourced when Django imports
the settings file. This repository also uses `local_settings.py` settings module
for more comprehensive configuration.

Create a basic file for development as follows

    echo 'DEBUG=True' > .env

File `local_settings.py` will be copied from `local_settings.py.tpl_dev` when VSCode
enviroment is started. If you choose not to use the preferred environment, copy this
file by hand before starting docker-compose environment.

#### Parkkihubi settings

- `PARKKIHUBI_PUBLIC_API_ENABLED` default `True`
- `PARKKIHUBI_MONITORING_API_ENABLED` default `True`
- `PARKKIHUBI_OPERATOR_API_ENABLED` default `True`
- `PARKKIHUBI_ENFORCEMENT_API_ENABLED` default `True`
- `PARKKIHUBI_DATA_API_ENABLED`default `True`

### Running tests

Run all tests

    py.test

Run with coverage

    py.test --cov-report html --cov .

Open `htmlcov/index.html` for the coverage report.

### Importing parking areas

To import Helsinki parking areas run:

    python manage.py import_parking_areas

### Geojson importers

To import payment zones from geojson run:

    python manage.py import_geojson_payment_zones --domain=HKI  <GEOJSON_FILE_PATH>

To import permit areas from geojson run:

    python manage.py import_geojson_permit_areas --domain=HKI <GEOJSON_FILE_PATH>

### Starting a development server

With VSCode environment, you can start development server from debug side-bar. You
also need to run migrations and generate static files.

    python manage.py migrate
    python manage.py collectstatic --noinput

Operator API will be available at [http://127.0.0.1:8000/operator/v1/](http://127.0.0.1:8000/operator/v1/)

Enforcement API will be available at
http://127.0.0.1:8000/enforcement/v1/

Public API will be available at [http://127.0.0.1:8000/public/v1/](http://127.0.0.1:8000/public/v1/)

### Generating API documentation

The API documentation conforms to [Swagger Specification 2.0](http://swagger.io/specification/).

Three possible ways (out of many) to generate the documentation:

- Run the documentation generating script:

      ./generate-docs

  The output will be in `docs/generated` directory by default.  If you
  want to generate to a different directory, give that directory as the
  first argument to the script.

- [bootprint-openapi](https://github.com/bootprint/bootprint-openapi)

    Probably the recommended way.

    Installation:

      npm install -g bootprint
      npm install -g bootprint-openapi

    Running (in `parkkihubi` repository root):

      bootprint openapi docs/api/enforcement.yaml </output/path/enforcement/>
      bootprint openapi docs/api/operator.yaml </output/path/operator/>

- [swagger-codegen](https://github.com/swagger-api/swagger-codegen)

    Due to [a bug in swagger-codegen](https://github.com/swagger-api/swagger-codegen/pull/4508),
    we're using an unreleased version at the moment.

    To build swagger-codegen from source, you need Apache maven installed (you'll
    need java 7 runtime at a minimum):

        # Ubuntu
        sudo apt-get install maven

    Clone swagger-codegen master branch and build it:

        git clone https://github.com/swagger-api/swagger-codegen
        cd swagger-codegen/
        mvn clean package  # Takes a few minutes

    The client will now be available at `modules/swagger-codegen-cli/target/swagger-codegen-cli.jar`.

    To build the docs, in `parkkihubi` repository root:

        cd docs/api
        java -jar /path/to/codegen/swagger-codegen-cli.jar generate \
          -i enforcement.yaml -l html2 -c config.json \
          -o /output/path/enforcement/
        java -jar /path/to/codegen/swagger-codegen-cli.jar generate \
          -i operator.yaml -l html2 -c config.json \
          -o /output/path/operator/

## License

[MIT](https://tldrlegal.com/license/mit-license)

## Parking hub and SCALE-UP

Parts of the Parkkihubi platform are being developed as part of European Union Horizon 2020 programme funded SCALE-UP project (grant agreement no. 955332).
