def get_rel_path(path):
    if len(path) > 0 and path[0] == '/':
        path = path[1:]
    return path


def get_lnt_path(path):
    if len(path) == 0 or path == '/':
        return '/'
    elts = path.split('/')
    elts = [e for e in elts if len(e) > 0]
    return '/' + '/'.join(elts)


def get_from_json_path(path, json_object):
    edge = json_object
    for element in path:
        edge = edge.get(element, None)
        if edge is None:
            return None
    return edge
