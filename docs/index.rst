
SPARC Curation Tools
====================

The **sparc-curation-tool** is part of the software that is used in the collection of tools used for mapping data to scaffolds.

.. note::

   This project is under active development.

Install
-------

SPARC dataset tools can be installed from PyPi.org with the following command::

  pip install sparc-curation-tool

Usage
-----

**Scaffold Annotations:**

How to use (can also be found using :code:`scaffold-annotations -h`):

usage: :code:`scaffold_annotations.py [-h] [-m MAX_SIZE] [-r] [-f] dataset_dir`

Check scaffold annotations for a SPARC dataset.

**positional arguments:**

================== =======================================================
  dataset_dir       root directory for dataset that need to be annotated.
================== =======================================================
                        

**optional arguments:**

==================================== ======================================================
  -h, --help                         show this help message and exit
  -m MAX_SIZE, --max-size MAX_SIZE   Set the max size for metadata file. Default is 2MiB
  -r, --report                       Report any errors that were found.
  -f, --fix                          Fix any errors that were found.
==================================== ======================================================


**Plot Annotations:**

How to use (can also be found using :code:`plot-annotation -h`):

usage: :code:`plot-annotation.exe [-h] [-x X_AXIS_COLUMN] [-y [Y_AXES_COLUMNS ...]] [-n] [-r] [-d {tab,comma}] {heatmap,timeseries}`

Create an annotation for a SPARC plot. The Y_AXES_COLUMNS can either be single numbers or a range in the form 5-8. The start and end numbers are included in the range. The -y/--y-axes-columns argument will consume the    
positional plot type argument. That means the positional argument cannot follow the -y/--y-axes-columns.

positional arguments:
  {heatmap,timeseries}  must define a plot type which is one of; heatmap, timeseries.

**positional arguments:**

================== =======================================================
  dataset_dir       root directory for dataset that need to be annotated.
================== =======================================================
                        

**optional arguments:**

================================================================= ==========================================================================================================================================
  {heatmap,timeseries}                                            must define a plot type which is one of; heatmap, timeseries.
  -h, --help                                                      show this help message and exit
  -x X_AXIS_COLUMN, --x-axis-column X_AXIS_COLUMN                 integer index for the independent column (zero based). Default is 0.
  -y [Y_AXES_COLUMNS ...], --y-axes-columns [Y_AXES_COLUMNS ...]  list of indices for the dependent columns (zero based). Can be used multiple times. Can be specified as a range e.g. 5-8. Default is [].
  -n, --no-header                                                 Boolean to indicate whether a header line is missing. Default is False.
  -r, --row-major                                                 Boolean to indicate whether the data is row major or column major. Default is False.
  -d {tab,comma}, --delimiter {tab,comma}                         The type of delimiter used, must be one of; tab, comma. Default is comma.
================================================================= ==========================================================================================================================================

Run
---

To run the application create a virtual environment.

::

  python -m venv venv_sparc

Activate the virtual environment::

  source venv_sparc/bin/activate

For bash shells, or::

  venv_sparc\Scripts\activate

For a windows :code:`cmd` prompt.

With the activated virtual environment install the package.

::

  pip install sparc-curation-tools

Then execute the application to print out the usage information to test the script.

**Scaffold Annotations** 

::

  scaffold-annotations -h

**Plot Annotations** 

::

  plot-annotations -h

Examples:
---------

**Scaffold Annotations** 

::

  scaffold-annotations <dataset_dir>

**Plot Annotations** 

::

  plot-annotations <dataset_dir>