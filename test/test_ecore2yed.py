import logging

from ecore2yed import create_graph_from_file

# create logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)


def test_loads_bpmn():
    with open('bpmn20.ecore', 'r',) as fin:
        g = create_graph_from_file(fin, False)
    print(g)
