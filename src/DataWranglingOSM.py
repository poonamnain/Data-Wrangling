# Data Wrangling project
# File name DataWranglingOSM.py
# Keep your downloaded XML file MorganHill.xml in the folder path

# Read your xml file, write it to csv using pythod code
# Create db with below command
# sqlite3 MorganHill.db

import csv
import codecs  
import pprint
import re
import xml.etree.cElementTree as ET
import cerberus
import schema # note: refers to the schema.py file attached in this directory  

OSM_FILE = "MorganHill.xml"
NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "node_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
STREET_TYPE_RE = re.compile(r'\b\S+\.?$', re.IGNORECASE)
PHONE_RE = re.compile (r'\s*(\+1)?[- ]?\(?(\d{3})\)?[\- ]?(\d{3})[- ]?(\d{4})\s*')
SCHEMA = schema.schema

NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset',
               'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp'] 
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type'] 
WAY_NODES_FIELDS = ['id', 'node_id', 'position'] 

STREET_TYPE_MAPPING = { "Ave": "Avenue",
                       "Ave.": "Avenue",
                       "Dr": "Drive"}
EXPECTED = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place",
            "Square", "Lane", "Road", "Trail", "Parkway", "Commons",
            "Circle", "Grande", "Way"]


# ================================================== #
#               Helper Functions                     #
# ================================================== #

class UnicodeDictWriter(csv.DictWriter, object):   
    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def get_element(osm_file, tags=('node', 'way', 'relation')):
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()

            
def shape_element(element, problem_chars = PROBLEMCHARS,
                  default_tag_type = 'regular'):


    def get_tags(element, tag_id):
        elem_tags = []
        tag_type = element.tag
        for tag in element.iter('tag'):
            tag_attribs = {}
            for name, value in tag.items():
                if name == 'k':
                    tag_attribs['key'] = value
                elif name == 'v':
                    tag_attribs['value'] = value
                else:
                    tag_attribs[name] = value
                tag_attribs['type'] = tag_type
                tag_attribs['id'] = tag_id
                
            if tag_attribs['key'] == 'addr:street':
                tag_attribs['value'] = update_name(tag_attribs['value'])
            if tag_attribs['key'] == 'contact:phone' or tag_attribs['key']=='phone':
                tag_attribs['value'] = update_phone(tag_attribs['value'])               
            elem_tags.append(tag_attribs)
        return elem_tags


    def get_way_nodes(element, way_id):
        way_nodes = []
        position = 0
        for way_node in element.iter('nd'):
            way_node_attribs = {}
            for name, value in way_node.items():
                if name == 'ref':
                    way_node_attribs['node_id'] = value
            way_node_attribs['id'] = way_id
            way_node_attribs['position'] = position
            way_nodes.append(way_node_attribs)
            position = position + 1
        return way_nodes

 
    node_attribs = {}
    way_attribs = {}
    tags = []
    if element.tag == 'node':
        for name, value in element.items():
            node_attribs[name] = value
        tags = get_tags(element, node_attribs['id'])
        return {'node': node_attribs, 'node_tags': tags}

    if element.tag == 'way':
        for name, value in element.items():
            way_attribs[name] = value
        tags = get_tags(element, way_attribs['id'])
        way_nodes = get_way_nodes(element, way_attribs['id'])
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}

    
def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = list(validator.errors.items())[0]
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        raise Exception(message_string.format(field, error_string)) 


def update_name(name, mapping=STREET_TYPE_MAPPING):
    m = STREET_TYPE_RE.search(name)
    if m:
        street_type = m.group()
        if street_type in mapping.keys():
            better_name = re.sub(street_type, mapping[street_type], name)
            print (name, "=>", better_name)
            return better_name
        elif street_type not in EXPECTED:
            print ('Unknown street type: ', street_type)
    return name


def update_phone(phone):
    m = PHONE_RE.search(phone)
    better_phone = phone
    if m:
        if m.group(1) is None:
            country_code = '+1'
        else:
            country_code = m.group(1)
        area_code = m.group(2)
        local_num1 = m.group(3)
        local_num2 = m.group(4)
        better_phone = country_code+' '+area_code+'-'+local_num1+'-'+local_num2     
        print (phone, "=>", better_phone)
    else:
        print ('Unknown phone type: ', phone)
    return better_phone


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
            codecs.open(NODE_TAGS_PATH, 'w') as node_tags_file, \
            codecs.open(WAYS_PATH, 'w') as ways_file, \
            codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file, \
            codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file:        


        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(node_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)


        nodes_writer.writeheader() 
        node_tags_writer.writeheader() 
        ways_writer.writeheader() 
        way_tags_writer.writeheader() 
        way_nodes_writer.writeheader() 
 
        validator = cerberus.Validator()
        
        for element in get_element(file_in, tags=('node', 'way')):                 
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags']) 

            
if __name__ == '__main__':
    process_map(OSM_FILE, validate=True) 