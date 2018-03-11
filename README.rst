================
pytest-docker-db
================

.. image:: https://travis-ci.org/kprestel/pytest-docker-db.svg?branch=master
    :target: https://travis-ci.org/kprestel/pytest-docker-db
    :alt: See Build Status on Travis CI

A plugin to use docker databases for pytests

----

This `Pytest`_ plugin was generated with `Cookiecutter`_ along with `@hackebrot`_'s `Cookiecutter-pytest-plugin`_ template.


Features
--------

* TODO


Requirements
------------

* docker-py>=1.10.6
* pytest>=3.3.2


Installation
------------

You can install "pytest-docker-db" via `pip`_ from `PyPI`_::

    $ pip install pytest-docker-db


Usage
-----

Plugin contains one fixture:
     *docker_db* - it's session scoped and returns a `docker-py container` object. For almost all use cases
        the user will not care about this object.



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
