================
pytest-docker-db
================

.. image:: https://travis-ci.org/kprestel/pytest-docker-db.svg?branch=master
    :target: https://travis-ci.org/kprestel/pytest-docker-db
    :alt: See Build Status on Travis CI

A plugin to use docker databases for pytests

----

This `Pytest`_ plugin was generated with `Cookiecutter`_ along with `@hackebrot`_'s `Cookiecutter-pytest-plugin`_
template.

What is this?
-------------
This is a pytest plugin that hooks into the host's :code:`docker` daemon to create and teardown containers within the pytest
life cycle.


Features
--------
* Use custom :code:`Dockerfile`\s or base images from `Dockerhub`_
* Use :code:`volumes` to persist test data in between testing sessions
* Specify what port you want the container to be listening on the host machine and the container
* Optionally persist the container between test sessions
* Name the containers created

Requirements
------------

* docker-py>=1.10.6
* pytest>=3.3.2
* docker


Installation
------------

You can install "pytest-docker-db" via `pip`_ from `PyPI`_::

    $ pip install pytest-docker-db


Configuration
-------------

* db-volume-args

    * Provide the "-v" arguments that you would pass to the
      "docker run" command if you were using the cli. If you need
      multiple volumes mounted separate them with commas.
    * The basic syntax is :code:`/host/vol/path:/path/in/container:rw`.
      If using a named volume, the syntax would be :code:`vol-name:/path/in/container:rw`
      'For more information please visit the `docker documentation`_'

* db-image

    * Specify the name of the image to use as the DB.

        * Must be in the form of :code:`"image_name":"tag"`.

* db-name

    * Specify the name of the container. If this is not specified a random container name will be
      used with the prefix :code:`docker-db`

* db-host-port

    * Specify the port that the db should be listening to on the host machine.

* db-port

    * Specify the port that the db should be listening to in the container.
      This is often the default port used by your database.

* db-persist-container

    * If set, the container created will not be torn down after the test suite has ran.
      By default any image created will be torn down and removed after the test suite has finished.

* db-dockerfile

    * Specify the name of the Dockerfile within the directory set as the :code:`db-build-context`

        * If a path is given as well as an image name, the Dockerfile will be used.

* db-docker-context

    * The directory to use as the docker build context.



Usage
-----

Plugin contains one fixture:
     *docker_db* - it's a session scoped fixture that returns a `docker-py container` object.
     For almost all use cases the user will not care about this object.

The recommended way to use this fixture is to create an :code:`autouse=True` fixture in your :code:`conftest.py` file
to automatically invoke the setup of the containers.

::

    @pytest.fixture(scope='session', autouse=True)
    def my_docker_db(docker_db):
        pass

Can be configured via the :code:`pytest` CLI or the :code:`pytest.ini` file.

pytest.ini:
::

    [pytest]
    db-volume-args=/home/kp/vol:/var/lib/postgresql/data:rw
    db-image=postgres:latest
    db-name=test-postgres
    db-port=5432
    db-host-port=5434

pytest CLI using a `Dockerhub`_ image :
::

    $ pytest --db-image=postgrest:latest --db-name=test-postgres --db-port=5432 --db-host-port=5434

pytest CLI using a custom image:
::

    $ pytest --db-dockerfile=Dockerfile --db-name=test-postgres --db-port=5432 --db-host-port=5434

Contributing
------------
Contributions are very welcome. Tests can be run with `tox`_, please ensure
the coverage at least stays the same before you submit a pull request.

License
-------

Distributed under the terms of the `MIT`_ license, "pytest-docker-db" is free and open source software


Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

.. _`Cookiecutter`: https://github.com/audreyr/cookiecutter
.. _`@hackebrot`: https://github.com/hackebrot
.. _`MIT`: http://opensource.org/licenses/MIT
.. _`BSD-3`: http://opensource.org/licenses/BSD-3-Clause
.. _`GNU GPL v3.0`: http://www.gnu.org/licenses/gpl-3.0.txt
.. _`Apache Software License 2.0`: http://www.apache.org/licenses/LICENSE-2.0
.. _`cookiecutter-pytest-plugin`: https://github.com/pytest-dev/cookiecutter-pytest-plugin
.. _`file an issue`: https://github.com/kprestel/pytest-docker-db/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.python.org/pypi/pip/
.. _`PyPI`: https://pypi.python.org/pypi
.. _`docker-py container`: http://docker-py.readthedocs.io/en/stable/containers.html
.. _`Dockerhub`: https://hub.docker.com/
.. _`docker documentation`: https://docs.docker.com/storage/volumes/#start-a-container-with-a-volume
