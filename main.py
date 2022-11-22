import pyshacl
from rdflib import Graph, term, query
import xml.etree.ElementTree as XML
import json

# term.URIRef

ontology = Graph()
ontology.parse('./ontology_raw.owl', format='application/rdf+xml')

data = Graph()
# data.parse('./dados_conectados_mobed.ttl', format='ttl')
# data.parse('./data_perfect.ttl', format='ttl')
data.parse('./both.ttl', format='ttl')

shacl = Graph()
# shacl.parse('./shacl.rq', format='ttl')
shacl.parse('./real_shacl.rq', format='ttl')

result = pyshacl.validate(data_graph=data, ont_graph=ontology,
                          shacl_graph=shacl,
                          inference='both',
                        #   inference='owlrl',
                        #   inference='rdfs',
                        #   inference='none',
                          abort_on_first=False,
                          allow_infos=False,
                          allow_warnings=False,
                          meta_shacl=False,
                          advanced=False,
                          js=False,
                          debug=False)
conforms, results_graph, results_text = result

results_graph.serialize(format="xml", destination='res.xml')
tree = XML.parse('./res.xml')
root = tree.getroot()

broken: XML.Element = []
duplicates_sparql: XML.Element = []
for item in root:
    if item.find('{http://www.w3.org/ns/shacl#}resultSeverity') is not None:
        broken.append(item)

checked_attrs = []
valids = []
for item in broken:
    if 'http://www.w3.org/ns/shacl#SPARQLConstraintComponent' in item.find('{http://www.w3.org/ns/shacl#}sourceConstraintComponent').attrib.values():
        duplicates_sparql.append(item)
        focus = item.find(
            '{http://www.w3.org/ns/shacl#}focusNode').attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource']

        jquery = '''
        SELECT ?code
        WHERE {
            <%s> <http://www.semanticweb.org/mateus/ontologies/2019/9/mobility_&_education#hasCode> ?code
        }
        ''' % focus

        qres = data.query(jquery)

        for row in qres:
            values = row.asdict()
            code = values['code']
            if(code in checked_attrs):
                continue
            checked_attrs.append(code)

            verify = '''
                SELECT ?res
                WHERE {
                    ?res <http://www.semanticweb.org/mateus/ontologies/2019/9/mobility_&_education#hasCode> %d
                }
            ''' % code.value
            duplicates = data.query(verify)

            tree = XML.fromstring(duplicates.serialize())
            root = tree

            duplicates_raw: XML.Element = list(root.iter(
                '{http://www.w3.org/2005/sparql-results#}uri'))
            for i in duplicates_raw:
                i_value = i.text
                for j in duplicates_raw:
                    j_value = j.text
                    if(i_value == j_value):
                        continue

                    is_same_query = '''
                        PREFIX owl: <http://www.w3.org/2002/07/owl#>

                        SELECT ?res
                        WHERE {
                            <%s> <http://www.w3.org/2002/07/owl#sameAs> <%s>
                        }
                    ''' % (i_value, j_value)
                    is_same = data.query(is_same_query)
                    if(len(is_same) > 0):
                        valids.extend([i_value, j_value])

valids = list(set(valids))
for broke in broken:
    focus = broke.find(
        '{http://www.w3.org/ns/shacl#}focusNode').attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource']
    data = broke.find(
        '{http://www.w3.org/ns/shacl#}resultMessage').text
    print('****************************')
    try:
        data = json.loads(data)
        if(data['type'] == 'duplicate'):
            if(focus in valids):
                continue
        print(data['message'])
    except:
        print(data)
    print(focus)
    print('****************************')
