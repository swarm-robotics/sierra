Contributing
============

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   variable.rst
   graphs.rst
   models.rst
   project.rst

First, install additional dependencies::

  pip3 pytype pylint mypy

General Workflow
----------------

For the general contribution workflow, see the docs over in :xref:`LIBRA`.

For the static analysis step:

#. Run the following on the code from the root of SIERRA::

     pytype -k .

   Fix ANY and ALL errors that arise, as SIERRA should get a clean bill of health
   from the checker.

#. Run the following on any module directories you changed, from the root of
   SIERRA::

     pylint <directory name>

   Fix ANY errors your changes have introduced (there will probably still be
   errors in the pylint output, because cleaning up the code is always a work in
   progress).

#. Run the following on any module directories you changed, from the root of
   SIERRA::

     mypy --ignore-missing-imports --warn-unreachable <directory name>

   Fix ANY errors your changes have introduced (there will probably still be
   errors in the my output, because cleaning up the code is always a work in
   progress).
