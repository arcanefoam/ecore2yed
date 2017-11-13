#ecore2yed

ECore 2 YEd is a Python script to export [EMF](https://www.eclipse.org/modeling/emf/) metamodels as a
[YEd](http://www.yworks.com/products/yed) graph (i.e. a graphml graph with additional formatting information).

The purpose of the script is to take advantage of YEd's advanced features (layouts, formatting, high-res export) in
order to produce high-quality images of the metamodel for use in publications and/or slides.

## Usage
You need to install the lxml package in your machine (Windows users might want to use [Conda](https://conda.io/docs/)
to make this step easier).

External reference resolution is not fully supported. The script assumes that external references provide the metamodel
location and that the location is accessible from where the script is run.

usage: ecore2yed.py [-h] [-e] [-o OUTPUT] [-v] input

positional arguments:
  input          the input ecore file (*.ecore)

optional arguments:
  -h, --help     show this help message and exit
  -e             create nodes for external references.
  -o OUTPUT      the output yed file (*.graphml). If missing, same location as
                 input
  -v, --verbose  enables output messages (infos, warnings)


