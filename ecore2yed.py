import argparse
import configparser
import logging
import os
import warnings
import re

from lxml import etree

descmsg = 'Transform an Ecore metamodel to yed (graphml). For EReferences across metamodels, it assumes that the' \
          'referenced metamodel is accessible.'

url_regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

base_height = 30
attribute_height = 18


class EcoreReferenceError(Exception):
    pass


def get_key_id():
    """
    Generate auto-incrementing key ids
    :return:
    """
    number = 0
    while True:
        yield 'd{}'.format(number)
        number += 1


def get_node_id():
    """
    Generate auto-incrementing node ids
    :return:
    """
    number = 0
    while True:
        yield 'n{}'.format(number)
        number += 1


def get_edge_id():
    """
    Generate auto-incrementing edge ids
    :return:
    """
    number = 0
    while True:
        yield 'e{}'.format(number)
        number += 1

# Namespaces
GRAPHML_NAMESPACE = 'http://graphml.graphdrawing.org/xmlns/graphml' # FIXME maybe the last segment is not needed?
XSI_NAMESPACE = 'http://www.w3.org/2001/XMLSchema-instance'
YWORKS_NAMESPACE = 'http://www.yworks.com/xml/graphml'
XMI_NAMESPACE = 'http://www.omg.org/XMI'
ECORE_NAMESPACE = "http://www.eclipse.org/emf/2002/Ecore"

xsi_ns = '{{{0}}}'.format(XSI_NAMESPACE)
gml_ns = '{{{0}}}'.format(GRAPHML_NAMESPACE)
y_ns = '{{{0}}}'.format(YWORKS_NAMESPACE)
xmi_ns = '{{{0}}}'.format(XMI_NAMESPACE)
ecore_ns = '{{{0}}}'.format(ECORE_NAMESPACE)

element_to_node = dict()
node_to_element = dict()
xmi_id_to_element = dict()  # Map xmi IDs to yed ids

# Ecore location

head = ""
tail = ""


def get_element_for_node(node):
    return node_to_element[node]


def get_node_for_element(element):
    try:
        return element_to_node[element]
    except KeyError:
        return None


def set_node_for_element(element, node):
    element_to_node[element] = node
    node_to_element[node] = element


def add_ecore_class_to_graph():
    """
    For metamodels that have EReferences and/or ESuperTypes to ECore classes, we can add this known EClasses to the
    graph
    :return:
    """
    pass


def bounds_to_string(lower, upper):
    bounds = ''
    if lower != upper:      # lower > 0 and upper != 0 and
        if upper == -1:
            upper = '*'
        bounds = '{}..{}'.format(lower, upper)
    elif lower == 1:
        bounds = str(lower)
    # else:
    #    raise Exception('The multi-value bounds are not correct.')
    return bounds


class Element:

    def __init__(self, shape_id, desc_id):

        self.graphics = etree.Element('data', key=shape_id)
        self.desc = etree.Element('data', key=desc_id)


class EClassNode(Element):
    """
    Nodes to represent EClasses
    """

    def __init__(self, id, abstract, *args, external=False):
        """
        Create a new EClass node.
        :param id: the node id
        :param abstract: True if the class is abstract
        :param args: Additional format arguments
        :param external: If the EClass is external (i.e. referenced metamodel)
        """
        super().__init__(*args)
        self.node = etree.Element('node', id=id)
        self.id = id
        self.generic_node = etree.Element(y_ns + 'GenericNode',
                                          configuration='com.yworks.entityRelationship.big_entity')
        etree.SubElement(self.generic_node, y_ns + 'Fill', hasColor="false", transparent="false")
        if external:
            etree.SubElement(self.generic_node, y_ns + 'BorderStyle', color="#000000", type="dashed", width="1.0")
        fontStyle = 'plain'
        if abstract == 'true':
            fontStyle = 'italic'
        self.node_label = etree.Element(y_ns + 'NodeLabel',
                                        configuration='com.yworks.entityRelationship.label.name',
                                        autoSizePolicy='content',
                                        modelName='internal',
                                        modelPosition='t',
                                        backgroundColor='#FFFFFF',
                                        fontStyle=fontStyle)
        self.generic_node.append(self.node_label)

        self.attr_label = etree.Element(y_ns + 'NodeLabel',
                                        configuration='com.yworks.entityRelationship.label.attributes',
                                        autoSizePolicy='content',
                                        alignment="left",
                                        modelName='custom')
        label_model = etree.Element(y_ns + 'LabelModel')
        etree.SubElement(label_model, y_ns + 'ErdAttributesNodeLabelModel')
        self.attr_label.append(label_model)
        model_parameter = etree.Element(y_ns + 'ModelParameter')
        etree.SubElement(model_parameter, y_ns + 'ErdAttributesNodeLabelModelParameter')
        self.attr_label.append(model_parameter)
        self.generic_node.append(self.attr_label)
        style = etree.Element(y_ns + 'StyleProperties')
        property = etree.Element(y_ns + 'Property', name='y.view.ShadowNodePainter.SHADOW_PAINTING', value='true')
        property.attrib['class'] = 'java.lang.Boolean'
        style.append(property)
        self.generic_node.append(style)

        self.graphics.append(self.generic_node)
        self.node.append(self.graphics)
        self.node.append(self.desc)

    def set_label_text(self, label):
        """
        Set the node label's text
        :param label:
        :return:
        """
        self.node_label.text = label

    def add_eattribute(self, name, attrtype, lower, upper, hide_mult, external=False):
        """
        Add an EAttribute to the node. Attributes are appended to the node's attribute label
        :param name: The name of the attribute
        :param attrtype: The type of the attribute
        :param lower: The lower bound of the attribute
        :param upper: The upper bound of the attribute
        :return:
        """
        frmt_attr = "{0} : {1} {2}"
        if hide_mult:
            frmt_attr = "{0} : {1}"
        bounds = '[{}]'.format(bounds_to_string(lower, upper))
        if external:
            attrtype = f"({attrtype})"
        if self.attr_label.text is None:
            self.attr_label.text = frmt_attr.format(name, attrtype, bounds)
        else:
            self.attr_label.text += "\n" + frmt_attr.format(name, attrtype, bounds)


class EReferenceEdge(Element):
    """
    EReferences are represented by edges in the graph
    """

    def __init__(self, id, source, target, *args, containment=False, inheritance=False):
        """
        Create a new EReference edge
        :param id: The edge id
        :param source: The source node (from an EClass)
        :param target: The target node (from an EClass)
        :param args: Additional format arguments
        :param containment: If the reference is containment
        :param inheritance: If the reference is inheritance
        """

        super().__init__(*args)
        self.edge = etree.Element('edge', id=id, source=source, target=target)
        self.id = id
        self.polyline_edge = etree.Element(y_ns + 'PolyLineEdge')
        self.graphics.append(self.polyline_edge)
        self.edge.append(self.graphics)
        self.edge.append(self.desc)
        self.arrows = etree.Element(y_ns + 'Arrows')
        if containment:
            self.arrows.attrib['source'] = 'diamond'
            self.arrows.attrib['target'] = 'none'
        elif inheritance:
            self.arrows.attrib['source'] = 'white_delta'
            self.arrows.attrib['target'] = 'none'
        else:
            self.arrows.attrib['source'] = 'none'
            self.arrows.attrib['target'] = 'plain'
        self.polyline_edge.append(self.arrows)

    def create_labels(self, target_name, target_mult):
        """
        Create the labels if the edge is new
        :param target_name:
        :param target_mult:
        :return:
        """
        # Name
        target_label = etree.Element(y_ns + 'EdgeLabel', modelName='six_pos', modelPosition='ttail',
                                          preferredPlacement='target_right')
        target_label.text = target_name
        placement = etree.Element(y_ns + 'PreferredPlacementDescriptor', placement='target', side='right',
                                  sideReference='relative_to_edge_flow')
        target_label.append(placement)
        self.polyline_edge.append(target_label)
        # Multiplicity
        target_mult_label = etree.Element(y_ns + 'EdgeLabel', modelName='six_pos', modelPosition='thead',
                                          preferredPlacement='target_left')
        target_mult_label.text = target_mult
        placement = etree.Element(y_ns + 'PreferredPlacementDescriptor', placement='target', side='left',
                                  sideReference='relative_to_edge_flow')
        target_mult_label.append(placement)
        self.polyline_edge.append(target_mult_label)

    def add_labels(self, containment, source_name=None, source_mult=None):
        """
        If an edge existed, we can only modify the values
        :param containment:
        :param source_name:
        :param source_mult:
        :return:
        """
        if containment:
            self.arrows.attrib['target'] = 'diamond'
            self.arrows.attrib['source'] = 'none'
        # Opposite Name
        source_label = etree.Element(y_ns + 'EdgeLabel', modelName='six_pos', modelPosition='shead',
                                     preferredPlacement='source_left')
        source_label.text = source_name
        placement = etree.Element(y_ns + 'PreferredPlacementDescriptor', placement='source', side='left',
                                  sideReference='relative_to_edge_flow')
        source_label.append(placement)
        self.polyline_edge.append(source_label)
        # Multiplicity
        source_mult_label = etree.Element(y_ns + 'EdgeLabel', modelName='six_pos', modelPosition='stail',
                                    preferredPlacement='source_right')
        source_mult_label.text = source_mult
        placement = etree.Element(y_ns + 'PreferredPlacementDescriptor', placement='source', side='right',
                                  sideReference='relative_to_edge_flow')
        source_mult_label.append(placement)
        self.polyline_edge.append(source_mult_label)


class Graph:

    def __init__(self, edgedefault='directed'):
        self.logger = logging.getLogger(__name__)
        nsmap = {None: GRAPHML_NAMESPACE, 'xsi': XSI_NAMESPACE, 'y': YWORKS_NAMESPACE}  # the default namespace (no prefix)
        self.root = etree.Element('graphml', id='G', edgedefault=edgedefault, nsmap=nsmap)
        self.root.attrib[xsi_ns+'schemaLocation'] = 'http://graphml.graphdrawing.org/xmlns ' \
                                                         'http://www.yworks.com/xml/schema/graphml/1.0/ygraphml.xsd'
        # Yed uses at least node/edge graphics and description
        key_id = get_key_id()
        self.node_graph_key = self.new_key(next(key_id), 'node')
        self.node_graph_key.attrib['yfiles.type'] = 'nodegraphics'
        self.edge_graph_key = self.new_key(next(key_id), 'edge')
        self.edge_graph_key.attrib['yfiles.type'] = 'edgegraphics'
        self.node_desc_key = self.new_key(next(key_id), 'node')
        self.node_desc_key.attrib['attr.name'] = 'description'
        self.node_desc_key.attrib['attr.type'] = 'string'
        self.edge_desc_key = self.new_key(next(key_id), 'edge')
        self.edge_desc_key.attrib['attr.name'] = 'description'
        self.edge_desc_key.attrib['attr.type'] = 'string'
        self.node_id = get_node_id()
        self.edge_id = get_edge_id()
        # Id references
        self.xmi_id_to_id = dict()      # Map xmi IDs to yed ids
        # EReferences
        self.sf_to_edge = dict()

    def new_key(self, id, target):
        key = etree.Element('key', id=id)
        key.attrib['for'] = target
        self.root.append(key)
        return key

    def add_eclass_node(self, element, external=False):
        """
        Add a new node to represent the
        :param element:
        :param external:
        :return:
        """
        xmi_id = element.attrib.get(xmi_ns + 'id', None)
        if xmi_id is not None:
            xmi_id_to_element[xmi_id] = element
        label = element.attrib['name']
        y_id = next(self.node_id)
        n = EClassNode(y_id, element.attrib.get('abstract', "false"), self.node_graph_key.attrib['id'],
                       self.node_desc_key.attrib['id'], external=external)
        if xmi_id is not None:
            self.xmi_id_to_id[xmi_id] = y_id
        n.set_label_text(label)
        self.root.append(n.node)
        set_node_for_element(element, n)

    def add_edge(self, source, target, containment=False, inheritance=False):
        """
        :param source: source node
        :param target: target element
        :return:
        """
        id = next(self.edge_id)
        e = EReferenceEdge(id, source, target, self.edge_graph_key.attrib['id'], self.edge_desc_key.attrib['id'],
                           containment=containment, inheritance=inheritance)
        self.root.append(e.edge)
        return e

    def add_node_attributes(self, tree, create_external, hide_mult, schema_location):
        for p in tree.iter():       #FIXME Multipackage?
            for c in p.iterdescendants(tag='eClassifiers'):
                for sf in c.iterdescendants(tag='eStructuralFeatures'):
                    self.add_eFeatures(c, sf, tree, create_external, hide_mult, schema_location)
                self.add_inheritance(c, tree, create_external, schema_location)

    def add_inheritance(self, c, tree, create_external, schema_location):
        try:
            super_types = c.attrib['eSuperTypes']
            for st in super_types.split(" "):
                resolved_type, _ = self.resolve_type(tree, st, create_external, schema_location)
                source = get_node_for_element(c)
                target = get_node_for_element(resolved_type)
                self.add_edge(target.id, source.id, inheritance=True)
        except KeyError:
            pass

    def add_eFeatures(self, clazz, sf, tree, create_external, hide_mult, schema_location):
        self.logger.info(f"Adding feature {sf.attrib['name']} to {clazz.attrib['name']}")
        try:
            eType = sf.attrib['eType']
        except KeyError:
            # Can have a nested eGenericType, assume is only child
            gt = sf[0]
            eType = gt.attrib['eClassifier']
        if ' ' in eType:  # The type is in another metamodel
            info = eType.split(' ')
            type_ref = info[1]
        else:  # The type is from the metamodel
            type_ref = eType
        resolved_type, external = self.resolve_type(tree, type_ref, create_external, schema_location)
        lower = int(sf.attrib.get('lowerBound', "0"))
        upper = int(sf.attrib.get('upperBound', "1"))
        if sf.attrib[xsi_ns + 'type'] == 'ecore:EAttribute':
            cn = get_node_for_element(clazz)
            if isinstance(resolved_type, type(sf)):
                resolved_type = resolved_type.attrib['name']
            cn.add_eattribute(sf.attrib['name'], resolved_type, lower, upper, hide_mult)
        elif external:
            cn = get_node_for_element(clazz)
            cn.add_eattribute(sf.attrib['name'], resolved_type, lower, upper, hide_mult, True)
        else:  # Create Edge
            source = get_node_for_element(clazz)
            target = get_node_for_element(resolved_type)
            containment = sf.attrib.get('containment', 'false')
            if containment == 'true':
                containment = True
            else:
                containment = False
            e = self.add_edge(source.id, target.id, containment=containment)
            self.sf_to_edge[sf] = e
            target_name = sf.attrib['name']
            target_mult = bounds_to_string(lower, upper)
            opp_name = None
            opp_mult = None
            # Edge Labels, opposite?
            opp_edge = None
            if 'eOpposite' in sf.attrib:
                eOpposite = sf.attrib['eOpposite']
                opp_prop_index = eOpposite.rfind('/')
                opp_type = sf.attrib['eOpposite'][:opp_prop_index]
                opp_element, _ = self.resolve_type(tree, opp_type, create_external, schema_location)
                opp_prop_name = sf.attrib['eOpposite'][opp_prop_index + 1:]
                xpath_exp = 'eStructuralFeatures[@name="{}"]'.format(opp_prop_name)
                opp_sf = opp_element.xpath(xpath_exp)
                assert len(opp_sf) == 1
                opp_sf = opp_sf[0]
                try:
                    opp_edge = self.sf_to_edge[opp_sf]
                except KeyError:
                    pass
                    # else:
                    # lower = int(opp_sf.attrib.get('lowerBound', "0"))
                    # upper = int(opp_sf.attrib.get('upperBound', "1"))
                    # opp_mult = bounds_to_string(lower, upper)
                    # opp_name = opp_sf.attrib['name']
                    # opp_edge.modify_labels(, opp_mult, )
            if opp_edge is None:
                e.create_labels(target_name, target_mult)
            else:
                opp_edge.add_labels(containment, target_name, target_mult)
                self.remove_edge(e)

    def create_eclass_nodes(self, package):
        """
        Create nodes in the graph to represent all EClasses in the package
        :param package: The package
        """
        for element in package.iterdescendants():
            try:
                if element.attrib[xsi_ns + 'type'] == 'ecore:EClass':
                    self.add_eclass_node(element)
            except KeyError:
                pass  # eAnnotations don't have a type

    def remove_edge(self, edge):
        self.root.remove(edge.edge)

    def resolve_type(self, tree, type_ref, create_external, schema_location):
        if '#' in type_ref:  # It is an xpath like reference
            info = type_ref.split('#')
            mm_ref = info[0]
            mm_type_path = info[1]
            if mm_ref == 'http://www.eclipse.org/emf/2002/Ecore':
                return mm_type_path.strip('/'), True
            else:
                if len(mm_ref) > 0:
                    return self.get_external_type(mm_ref, mm_type_path, create_external, schema_location)
                # '/1/Port'
                # '//EStringToStringMapEntry'
                # '//*[1]//*[2]//eClassifiers[@name=\'BDD\']'
                path_ref = mm_type_path.split('/')
                xpath_exp = []
                xpath_exp.append('//*[1]')
                for idx, path_idx in enumerate(path_ref[1:-1], start=1):
                    if path_ref[idx] == '':
                        # xpath_exp.append('*[1]')
                        pass
                    else:
                        path_index = int(path_ref[idx])
                        xpath_exp.append('*[{}]'.format(path_index + 1))
                xpath_exp.append('eClassifiers[@name="{}"]'.format(path_ref[-1]))
                xpath_exp = "//".join(xpath_exp)
                resolved_type = tree.xpath(xpath_exp)
                assert len(resolved_type) == 1
                resolved_type = resolved_type[0]
        else:  # It is an id
            resolved_type = xmi_id_to_element[type_ref]
        return resolved_type, False

    def get_external_type(self, mm_ref, mm_type_path, create_external, schema_location):
        if re.match(url_regex, mm_ref) is not None:
            # Check catalog
            try:
                ecore_file = os.path.join(head, schema_location[mm_ref])
            except KeyError:
                ecore_file = ""
        else:
            ecore_file = os.path.join(head, mm_ref)
        try:
            with open(ecore_file, 'r', ) as fin:
                tree = etree.parse(fin)
        except FileNotFoundError as e:
            warnings.warn("The metamodel ({}) for the external reference {} could not be loaded. Adding referenced "
                          "type as string. See --catalog option.".format(mm_ref, mm_type_path))
            epackage_name = "Unknown"
            create_external = False
        else:
            # Find the EPackage name
            epackage = tree.getroot()  # FIXME We assume 1 package
            epackage_name = epackage.attrib['name']

        type_name = mm_type_path.split('/')[-1]
        if create_external:
            for element in epackage.iterdescendants():
                try:
                    if element.attrib[xsi_ns + 'type'] == 'ecore:EClass':
                        if element.attrib['name'] == type_name:
                            self.add_eclass_node(element, external=True)
                            return element, False
                except KeyError:
                    pass  # eAnnotations don't have a type
            raise EcoreReferenceError("Type not found {} in metamodel {}. Make sure the source metamodel is valid."
                                      .format(mm_type_path, mm_ref))
        else:
            return "{}::{}".format(epackage_name, type_name), True


def create_graph_from_file(fin, create_external, hide_mult, schema_location):
    # Create a graph for the package.. one graph per package?
    tree = etree.parse(fin)
    fin.close()
    g = Graph()
    for element in tree.iter():
        if element.tag == ecore_ns + 'EPackage':
            g.create_eclass_nodes(element)
            g.add_node_attributes(tree, create_external, hide_mult, schema_location)  # This creates attributes and edges
            break  # FIXME What if more than one package? add_node_attributes should be called after all packages
    return g


def main():
    global head, tail
    parser = argparse.ArgumentParser(description=descmsg)
    parser.add_argument('input', type=str, help='the input ecore file (*.ecore)')
    parser.add_argument('-e',
                        action='store_true',
                        dest='create_external',
                        help='create nodes for external references.')
    parser.add_argument('-a',
                        action='store_true',
                        dest='hide_mult',
                        help='Hide multiplicities on attributes.')
    parser.add_argument('-o', type=str, dest='output',
                        help='the output yed file (*.graphml). If missing, same location as input')
    parser.add_argument('--catalog', type=str, dest='catalog',
                        help='Specifies catalog files to resolve external metamodel references. Supports the '
                             'configuration file format and expects a "Schema Location" section where keys are URIs and'
                             'values are file locations (locations can be absolute or relative to the input metamodel'
                             'path).')
    parser.add_argument('-v', '--verbose',
                        action='store_true', dest='verbose',
                        help='enables output messages (infos, warnings)')

    args = parser.parse_args()
    head, tail = os.path.split(args.input)
    config = configparser.ConfigParser(delimiters='=')

    if args.catalog is not None:
        config.read(args.catalog)
        print(config)
        print(config.sections())
    with open(args.input, 'r',) as fin:
        schema_location_ = {}
        if 'Schema Location' in config:
            schema_location_ = config['Schema Location']
        g = create_graph_from_file(fin, args.create_external, args.hide_mult, schema_location_)

    pretty = etree.tostring(g.root, pretty_print=True)
    encoded = pretty.decode('utf-8')
    if args.output is None:
        name = tail.split('.')[0]
        args.output = os.path.join(head, name + '.graphml')
    with open(args.output, 'w', encoding='utf-8') as fout:
        fout.write(encoded)
    print("Transcription finished.")


if __name__ == '__main__':
    main()
