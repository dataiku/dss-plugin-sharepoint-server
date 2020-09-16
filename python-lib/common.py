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
    # Given a array of nested fields, navigate to the terminal field and extract the value.
    node = json_object
    for element in path:
        node = node.get(element, None)
        if node is None:
            return None
    return node
