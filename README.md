# ecore2yed

ECore 2 YEd is a Python script to export [EMF](https://www.eclipse.org/modeling/emf/) metamodels as a
[YEd](http://www.yworks.com/products/yed) graph (i.e. a graphml graph with additional formatting information).

The purpose of the script is to take advantage of YEd's advanced features (layouts, formatting, high-res export) in
order to produce high-quality images of the metamodel for use in publications and/or slides. The scripts populates
classes, attributes and references. Formatting is kept to a minimum so the user can adjust it to her/his needs.

External reference resolution is not fully supported. The script assumes that external references provide the metamodel
location and that the location is accessible from where the script is run.

## Installation
You need to install the lxml package in your machine (Windows users might want to use [Conda](https://conda.io/docs/)
to make this step easier).

The project contains a Pipfile if you want to use [pipenv](https://docs.pipenv.org) in order to setup a virtual environment for the project. 

## Use

Running the script:

    $ python3 ecore2yed.py -h
    
    usage: ecore2yed.py [-h] [-e] [-a] [-o OUTPUT] [--catalog CATALOG] [-v] input         
    
    Transform an Ecore metamodel to yed (graphml). For EReferences across
    metamodels, it assumes that thereferenced metamodel is accessible.                    
    positional arguments:
    input              the input ecore file (*.ecore)
    
    optional arguments:                
      -h, --help         show this help message and exit
      -e                 create nodes for external references.
      -a                 Hide multiplicities on attributes.
      -o OUTPUT          the output yed file (*.graphml). If missing, same                
                         location as input                                                
      --catalog CATALOG  Specifies catalog files to resolve external metamodel            
                         references. Supports the configuration file format and           
                         expects a "Schema Location" section where keys are URIs          
                         andvalues are file locations (locations can be absolute          
                         or relative to the input metamodelpath).
      -v, --verbose      enables output messages (infos, warnings)                        
## Schema Location Catalog
When you model references types from other metamodels the script will try to resolve the type references. When the types come from a metamodel referenced by URI you need to provide a schema location catalog. The schema location catalog is a configuration file with the following format:
    
    [Schema Location]
    uri=path
    
where `uri` is the metamodel uri (e.g. `http://www.eclipse.org/emf/2002/Ecore`) and `path`is the location of the metamodel file. The path can be relative to the base metamodel or absoulte.