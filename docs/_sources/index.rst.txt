Welcome to zen's documentation!
===============================

.. image:: ./img/zen-logo.png
   :width: 200px
   :align: right
   :alt: zen Logo

`zen` is a Python package that provides a seamless interface for interacting with 
`Zenodo <https://zenodo.org>`_, a popular research data repository. It empowers researchers and 
developers to automate the management of their datasets and make them available through Zenodo, 
all from the convenience of Python scripts.

This documentation serves as a comprehensive guide to zen's features and functionalities. Use 
the navigation links below to explore the package's modules and learn how to harness the power 
of Zenodo for your research projects.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Background & Motivation
-----------------------

The **FAIR** principles stand for improving the **F**\indability, **A**\ccessibility, **I**\nteroperability, and **R**\euse of data by machines with minimal or no human intervention and were introduced by 
`Willkinson et al. (2016) <https://doi.org/10.1038/sdata.2016.18>`_ to deal with increasing data volume and complexity. Environmental data, driven by Earth Observation with satellite imagery, has already faced that challenge as many satellite image archives, such as those from NASA Landsat mission and ESA Copernicus missions become open, providing PB-scale data volumes for research and other exploration.  

Within the Open-Earth-Monitor Cyberinfrastructure project, a comprehensive survey was conducted where both environmental data users and producers were targeted to understand how they are familiar with FAIR principles in their data management. The survey results revealed that FAIR principles are considered important for geospatial data management but still lack implementation by many geospatial data users and providers. One of the reasons for that is the lack of resources and tools to make data more FAIR. Furthermore, both groups find it most important for data to be online findable and open. As a reflection to this feedback, the `zen` library has been introduced as an open tool to efficiently expose and manage data at the Zenodo repository, making such datasets findable.

Acknowledgements & Funding
--------------------------

This work is supported by `OpenGeoHub Foundation <https://opengeohub.org/>`_ and has received 
funding from the European Commission (EC) through the projects:

* `Open-Earth-Monitor Cyberinfrastructure <https://earthmonitor.org/>`_: Environmental information 
  to support EU’s Green Deal (1 Jun. 2022 – 31 May 2026 - 
  `101059548 <https://cordis.europa.eu/project/id/101059548>`_)
* `AI4SoilHealth <https://ai4soilhealth.eu/>`_: Accelerating collection and use of soil health 
  information using AI technology to support the Soil Deal for Europe and EU Soil Observatory 
  (1 Jan. 2023 – 31 Dec. 2026 - `101086179 <https://cordis.europa.eu/project/id/101086179>`_)

Licensed under the `MIT License <https://github.com/Open-Earth-Monitor/zen/blob/main/LICENSE>`_.
