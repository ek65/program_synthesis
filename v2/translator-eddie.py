import json

def load_json(filepath):
    with open(filepath, 'r') as json_file:
        data = json.load(json_file)
    return data

def parse_nodes(nodes):
    pass

def parse_edges(edges):
    pass

