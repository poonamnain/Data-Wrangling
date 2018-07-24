import xml.etree.cElementTree as ET
from collections import defaultdict
import re

OSM_FILE = "MorganHill.xml"
STREET_TYPE_RE = re.compile(r'\b\S+\.?$', re.IGNORECASE)
EXPECTED = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place",
            "Square", "Lane", "Road", "Trail", "Parkway", "Commons"]
        
def audit_func(osmfile, tags=('node', 'way')):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])                  
    osm_file.close()
    print (dict(street_types))
    return street_types


def is_street_name(way_node):
    if way_node.attrib['k'] == 'addr:street':
        return True
    else:
        return False


def audit_street_type(street_types, street_name):
    m = STREET_TYPE_RE.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in EXPECTED:
            street_types[street_type].add(street_name)
    return street_types


if __name__ == '__main__':
    audit_func(OSM_FILE)