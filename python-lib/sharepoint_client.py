import os, requests, sharepy
from requests_ntlm import HttpNtlmAuth

try:
    from BytesIO import BytesIO ## for Python 2
except ImportError:
    from io import BytesIO ## for Python 3

from sharepoint_constants import *
from dss_constants import *

class SharePointClient():

    def __init__(self, config):
        login_details = config.get('sharepoint_local')
        self.assert_login_details(DSS_LOCAL_DETAILS, login_details)
        self.setup_login_details(login_details)
        username = login_details['sharepoint_username']
        password = login_details['sharepoint_password']
        self.sharepoint_url = login_details['sharepoint_host']
        self.sharepoint_tenant = login_details['sharepoint_host']
        self.sharepoint_origin = login_details['sharepoint_host']
        self.session = LocalSharePointSession(
            username,
            password,
            self.sharepoint_origin,
            self.sharepoint_type,
            self.sharepoint_site,
            sharepoint_access_token = None
        )
        self.sharepoint_list_title = config.get("sharepoint_list_title")

    def setup_login_details(self, login_details):
        if 'sharepoint_type' in login_details:
            self.sharepoint_type = login_details['sharepoint_type']
        else:
            self.sharepoint_type = "sites"
        self.sharepoint_site = login_details['sharepoint_site']
        if 'sharepoint_root' in login_details:
            self.sharepoint_root = login_details['sharepoint_root'].strip("/")
        else:
            self.sharepoint_root = "Shared Documents"

    def get_folders(self, path):
        response = self.session.get(self.get_sharepoint_item_url(path) + "/Folders" )
        self.assert_response_ok(response)
        return response.json()

    def get_files(self, path):
        response = self.session.get(self.get_sharepoint_item_url(path) + "/Files" )
        self.assert_response_ok(response)
        return response.json()

    def get_sharepoint_item_url(self, path):
        URL_STRUCTURE = "{0}/{3}/{1}/_api/Web/GetFolderByServerRelativeUrl('/{3}/{1}/Shared%20Documents{2}')"
        if path == '/':
            path = ""
        return URL_STRUCTURE.format(self.sharepoint_origin, self.sharepoint_site, path, self.sharepoint_type)

    def get_file_content(self, full_path):
        response = self.session.get(
            self.get_file_content_url(full_path)
        )
        self.assert_response_ok(response)
        return response

    def write_file_content(self, full_path, data):
        full_path_parent, file_name = os.path.split(full_path)
        headers = {
            "Content-Length": "{}".format(len(data))
        }
        response = self.session.post(
            self.get_file_add_url(
                full_path_parent,
                file_name
            ),
            headers=headers,
            data=data
        )
        self.assert_response_ok(response)
        return response

    def create_folder(self, full_path):
        response = self.session.post(
            self.get_add_folder_url(full_path)
        )
        return response

    def move_file(self, full_from_path, full_to_path):
        response = self.session.post(
            self.get_move_url(
                full_from_path,
                full_to_path
            )
        )
        self.assert_response_ok(response)
        return response.json()

    def delete_file(self, full_path):
        headers = {
            "X-HTTP-Method":"DELETE"
        }
        response = self.session.post(
            self.get_file_url(full_path),
            headers = headers
        )
        self.assert_response_ok(response)

    def delete_folder(self, full_path):
        headers = {
            "X-HTTP-Method":"DELETE"
        }
        response = self.session.post(
            self.get_folder_url(full_path),
            headers = headers
        )
        self.assert_response_ok(response)

    def get_list_fields(self, list_title):
        url = self.get_list_fields_url(list_title)
        response = self.session.get(
            url
        )
        return response.json()

    def get_list_all_items(self, list_title):
        items = self.get_list_items(list_title)
        buffer = items
        while SHAREPOINT_RESULTS_CONTAINER_V2 in items and SHAREPOINT_NEXT_PAGE in items[SHAREPOINT_RESULTS_CONTAINER_V2]:
            items = self.session.get(items[SHAREPOINT_RESULTS_CONTAINER_V2][SHAREPOINT_NEXT_PAGE]).json()
            buffer[SHAREPOINT_RESULTS_CONTAINER_V2][SHAREPOINT_RESULTS].extend(items[SHAREPOINT_RESULTS_CONTAINER_V2][SHAREPOINT_RESULTS])
        return buffer

    def get_list_items(self, list_title):
        response = self.session.get(
            self.get_list_items_url(list_title)
        )
        self.assert_response_ok(response)
        return response.json()

    def create_list(self, list_name):
        headers={
            "content-type": APPLICATION_JSON,
            'Accept': 'application/json; odata=nometadata'
        }
        data = {
            '__metadata': {
                'type': 'SP.List'
            },
            'AllowContentTypes': True,
            'BaseTemplate': 100,
            'ContentTypesEnabled': True,
            'Title': list_name
        }
        response = self.session.post(
            self.get_lists_url(),
            headers=headers,
            json=data
        )
        self.assert_response_ok(response)
        return response

    def delete_list(self, list_name):
        headers={
            "X-HTTP-Method": "DELETE",
            "IF-MATCH" : "*"
        }
        response = self.session.post(
            self.get_lists_by_title_url(list_name),
            headers = headers
        )
        return response

    def create_custom_field(self, list_title, field_title):
        body = {
            'parameters' : {
                '__metadata': { 'type': 'SP.XmlSchemaFieldCreationInformation' },
                'SchemaXml':"<Field DisplayName='{0}' Format='Dropdown' MaxLength='255' Name='{0}' Title='{0}' Type='Text'></Field>".format(field_title)
            }
        }
        headers = {
            "content-type": APPLICATION_JSON
        }
        response = self.session.post(
            self.get_lists_add_field_url(list_title),
            headers = headers,
            json=body
        )
        self.assert_response_ok(response)
        return response

    def add_list_item(self, list_title, item):
        item["__metadata"] = {
            "type" : "SP.Data.{}ListItem".format(list_title.capitalize())
        }
        headers = {
            "Content-Type": APPLICATION_JSON
        }
        response = self.session.post(
            self.get_list_items_url(list_title),
            json=item,
            headers=headers
        )
        self.assert_response_ok(response)
        return response

    def get_base_url(self):
        return "{}/{}/{}/_api/Web".format(
            self.sharepoint_origin, self.sharepoint_type, self.sharepoint_site
        )

    def get_lists_url(self):
        return self.get_base_url() + "/lists"

    def get_lists_by_title_url(self, list_title):
        return self.get_lists_url() + "/GetByTitle('{}')".format(list_title)

    def get_list_items_url(self, list_title):
        return self.get_lists_by_title_url(list_title) + "/Items"

    def get_list_fields_url(self, list_title):
        return self.get_lists_by_title_url(list_title) + "/fields"

    def get_lists_add_field_url(self, list_title):
        return self.get_base_url() + "/GetList(@a1)/Fields/CreateFieldAsXml?@a1='/{}/{}/Lists/{}'".format(
            self.sharepoint_type,
            self.sharepoint_site,
            list_title
        )

    def get_folder_url(self, full_path):
        return self.get_base_url() + "/GetFolderByServerRelativeUrl({})".format(
            self.get_site_path(full_path)
        )

    def get_file_url(self, full_path):
        return self.get_base_url() + "/GetFileByServerRelativeUrl({})".format(
            self.get_site_path(full_path)
        )

    def get_file_content_url(self,full_path):
        return self.get_file_url(full_path) + "/$value"

    def get_move_url(self, from_path, to_path):
        return self.get_file_url(from_path) + "/moveto(newurl={},flags=1)".format(
            self.get_site_path(to_path)
        )

    def get_site_path(self, full_path):
        return "'/{}/{}/Shared%20Documents{}'".format(self.sharepoint_type, self.sharepoint_site, full_path)

    def get_add_folder_url(self, full_path):
        return self.get_base_url() + "/Folders/add('Shared%20Documents/{}')".format(
            full_path
        )

    def get_file_add_url(self, full_path, file_name):
        return self.get_folder_url(full_path) + "/Files/add(url='{}',overwrite=true)".format(file_name)

    def assert_login_details(self, required_keys, login_details):
        if login_details is None or login_details == {}:
            raise Exception("Login details are empty")
        for key in required_keys:
            if key not in login_details.keys():
                raise Exception(required_keys[key])

    def assert_response_ok(self, response):
        status_code = response.status_code
        if status_code == 404:
            raise Exception("Not found. Please check tenant, site type or site name.")
        if status_code == 403:
            raise Exception("Forbidden. Please check your account credentials.")

class SharePointSession():

    def __init__(self, sharepoint_user_name, sharepoint_password, sharepoint_tenant, sharepoint_site, sharepoint_access_token = None):
        self.sharepoint_tenant = sharepoint_tenant
        self.sharepoint_site = sharepoint_site
        self.sharepoint_access_token = sharepoint_access_token

    def get(self, url, headers = {}):
        headers["accept"] = APPLICATION_JSON
        headers["Authorization"] = self.get_authorization_bearer()
        return requests.get(url, headers = headers)

    def post(self, url, headers = {}, json=None, data=None):
        headers["accept"] = APPLICATION_JSON
        headers["Authorization"] = self.get_authorization_bearer()
        return requests.post(url, headers = headers, json=json, data=data)

    def get_authorization_bearer(self):
        return "Bearer {}".format(self.sharepoint_access_token)

class LocalSharePointSession():

    def __init__(self, sharepoint_user_name, sharepoint_password, sharepoint_origin, sharepoint_type, sharepoint_site, sharepoint_access_token = None):
        self.form_digest_value = None
        self.sharepoint_origin = sharepoint_origin
        self.sharepoint_type = sharepoint_type
        self.sharepoint_site = sharepoint_site
        self.sharepoint_access_token = sharepoint_access_token
        self.sharepoint_user_name = sharepoint_user_name
        self.sharepoint_password = sharepoint_password
        self.auth = HttpNtlmAuth(sharepoint_user_name, sharepoint_password)

    def get(self, url, headers = {}):
        headers["accept"] = APPLICATION_JSON
        return requests.get(url, headers = headers, auth=self.auth)

    def post(self, url, headers = {}, json=None, data=None):
        headers["accept"] = APPLICATION_JSON
        headers["X-RequestDigest"] = self.get_form_digest_value()
        return requests.post(url, headers = headers, json=json, data=data, auth=self.auth)

    def get_form_digest_value(self):
        if self.form_digest_value is not None:
            return self.form_digest_value
        headers={}
        headers["accept"] = APPLICATION_JSON_NOMETADATA
        response = requests.post(self.get_context_info_url(), headers = headers, auth=self.auth)
        json_response = response.json()
        if SHAREPOINT_FORM_DIGEST_VALUE in json_response:
            self.form_digest_value = json_response[SHAREPOINT_FORM_DIGEST_VALUE]
            return self.form_digest_value

    def get_context_info_url(self):
        return "{}/{}/{}/_api/contextinfo".format(
            self.sharepoint_origin, self.sharepoint_type, self.sharepoint_site
        )