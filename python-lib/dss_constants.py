class DSSConstants(object):
    APPLICATION_JSON = "application/json;odata=verbose"
    APPLICATION_JSON_NOMETADATA = "application/json; odata=nometadata"
    PATH = 'path'
    FULL_PATH = 'fullPath'
    EXISTS = 'exists'
    DIRECTORY = 'directory'
    IS_DIRECTORY = 'isDirectory'
    SIZE = 'size'
    LAST_MODIFIED = 'lastModified'
    CHILDREN = 'children'
    AUTH_OAUTH = "oauth"
    AUTH_LOGIN = "login"
    LOCAL_DETAILS = {
        "sharepoint_username": "The account's username is missing",
        "sharepoint_password": "The account's password is missing",
        "sharepoint_host": "The SharePoint host address is missing",
        "sharepoint_site": "The site name is missing"
    }
