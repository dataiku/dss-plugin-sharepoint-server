import os
import requests
import urllib.parse
import logging

from xml.etree.ElementTree import Element, tostring
from xml.dom import minidom
from requests_ntlm import HttpNtlmAuth
from sharepoint_constants import SharePointConstants
from dss_constants import DSSConstants
from common import get_from_json_path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='sharepoint-online plugin %(levelname)s - %(message)s')


class SharePointClientError(ValueError):
    pass


class SharePointClient():

    def __init__(self, config):
        logger.info("SharePointClient:1.0.4")
        self.sharepoint_site = None
        self.sharepoint_root = None
        login_details = config.get('sharepoint_local')
        self.assert_login_details(DSSConstants.LOCAL_DETAILS, login_details)
        self.setup_login_details(login_details)
        username = login_details['sharepoint_username']
        password = login_details['sharepoint_password']
        self.sharepoint_url = login_details['sharepoint_host']
        if 'ignore_ssl_check' in login_details:
            self.ignore_ssl_check = login_details['ignore_ssl_check']
        else:
            self.ignore_ssl_check = False
        self.sharepoint_tenant = login_details['sharepoint_host']
        self.sharepoint_origin = login_details['sharepoint_host']
        self.session = LocalSharePointSession(
            username,
            password,
            self.sharepoint_origin,
            self.sharepoint_site,
            sharepoint_access_token=None,
            ignore_ssl_check=self.ignore_ssl_check
        )
        self.sharepoint_list_title = config.get("sharepoint_list_title")

    def setup_login_details(self, login_details):
        self.sharepoint_site = login_details['sharepoint_site']
        if 'sharepoint_root' in login_details:
            self.sharepoint_root = login_details['sharepoint_root'].strip("/")
        else:
            self.sharepoint_root = "Shared Documents"

    def get_folders(self, path):
        response = self.session.get(self.get_sharepoint_item_url(path) + "/Folders")
        self.assert_response_ok(response)
        return response.json()

    def get_files(self, path):
        response = self.session.get(self.get_sharepoint_item_url(path) + "/Files")
        self.assert_response_ok(response)
        return response.json()

    def get_sharepoint_item_url(self, path):
        if path == '/':
            path = ""
        return SharePointConstants.GET_FOLDER_URL_STRUCTURE.format(
            self.sharepoint_origin,
            self.sharepoint_site,
            self.sharepoint_root,
            path
        )

    def get_file_content(self, full_path):
        response = self.session.get(
            self.get_file_content_url(full_path)
        )
        self.assert_response_ok(response, no_json=True)
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
            "X-HTTP-Method": "DELETE"
        }
        response = self.session.post(
            self.get_file_url(full_path),
            headers=headers
        )
        self.assert_response_ok(response, no_json=True)

    def delete_folder(self, full_path):
        headers = {
            "X-HTTP-Method": "DELETE"
        }
        self.session.post(
            self.get_folder_url(full_path),
            headers=headers
        )

    def get_list_fields(self, list_title):
        list_fields_url = self.get_list_fields_url(list_title)
        response = self.session.get(
            list_fields_url
        )
        self.assert_response_ok(response)
        return response.json()

    def get_list_all_items(self, list_title, column_to_expand=None):
        items = self.get_list_items(list_title, column_to_expand)
        buffer = items
        while SharePointConstants.RESULTS_CONTAINER_V2 in items and SharePointConstants.NEXT_PAGE in items[SharePointConstants.RESULTS_CONTAINER_V2]:
            items = self.session.get(items[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.NEXT_PAGE]).json()
            buffer[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS].extend(
                items[SharePointConstants.RESULTS_CONTAINER_V2][SharePointConstants.RESULTS]
            )
        return buffer

    def get_list_items(self, list_title, columns_to_expand=None):
        if columns_to_expand is not None:
            select = []
            expand = []
            for column_to_expand in columns_to_expand:
                if columns_to_expand.get(column_to_expand) is None:
                    select.append("{}".format(column_to_expand))
                else:
                    select.append("{}/{}".format(column_to_expand, columns_to_expand.get(column_to_expand)))
                    expand.append(column_to_expand)
            params = {
                "$select": ",".join(select),
                "$expand": ",".join(expand)
            }
        else:
            params = None
        response = self.session.get(
            self.get_list_items_url(list_title),
            params=params
        )
        self.assert_response_ok(response)
        return response.json()

    def create_list(self, list_name):
        headers = {
            "content-type": DSSConstants.APPLICATION_JSON,
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
        headers = {
            "X-HTTP-Method": "DELETE",
            "IF-MATCH": "*"
        }
        response = self.session.post(
            self.get_lists_by_title_url(list_name),
            headers=headers
        )
        return response

    def create_custom_field_via_id(self, list_id, field_title, field_type=None):
        field_type = SharePointConstants.FALLBACK_TYPE if field_type is None else field_type
        schema_xml = self.get_schema_xml(field_title, field_type)
        body = {
            'parameters': {
                '__metadata': {'type': 'SP.XmlSchemaFieldCreationInformation'},
                'SchemaXml': schema_xml
            }
        }
        headers = {
            "content-type": DSSConstants.APPLICATION_JSON
        }
        guid_lists_add_field_url = self.get_guid_lists_add_field_url(list_id)
        response = self.session.post(
            guid_lists_add_field_url,
            headers=headers,
            json=body
        )
        self.assert_response_ok(response)
        return response

    @staticmethod
    def get_schema_xml(encoded_field_title, field_type):
        field = Element('Field')
        field.set('encoding', 'UTF-8')
        field.set('DisplayName', encoded_field_title)
        field.set('Format', 'Dropdown')
        field.set('MaxLength', '255')
        field.set('Type', field_type)
        rough_string = tostring(field, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml()

    def add_list_item(self, list_title, item):
        item["__metadata"] = {
            "type": "SP.Data.{}ListItem".format(list_title.capitalize().replace(" ", "_x0020_"))
        }
        headers = {
            "Content-Type": DSSConstants.APPLICATION_JSON
        }
        response = self.session.post(
            self.get_list_items_url(list_title),
            json=item,
            headers=headers
        )
        self.assert_response_ok(response)
        return response

    def add_list_item_by_id(self, list_id, list_item_full_name, item):
        item["__metadata"] = {
            "type": "{}".format(list_item_full_name)
        }
        headers = {
            "Content-Type": DSSConstants.APPLICATION_JSON
        }
        list_items_url = self.get_list_items_url_by_id(list_id)
        response = self.session.post(
            list_items_url,
            json=item,
            headers=headers
        )
        self.assert_response_ok(response)
        return response

    def get_base_url(self):
        return "{}/{}/_api/Web".format(
            self.sharepoint_origin, self.sharepoint_site
        )

    def get_lists_url(self):
        return self.get_base_url() + "/lists"

    def get_lists_by_title_url(self, list_title):
        escaped_list_title = list_title.replace("'", "''")
        return self.get_lists_url() + "/GetByTitle('{}')".format(urllib.parse.quote(escaped_list_title))

    def get_lists_by_id_url(self, list_id):
        return self.get_lists_url() + "('{}')".format(list_id)

    def get_list_items_url(self, list_title):
        return self.get_lists_by_title_url(list_title) + "/Items"

    def get_list_items_url_by_id(self, list_id):
        return self.get_lists_by_id_url(list_id) + "/Items"

    def get_list_fields_url(self, list_title):
        return self.get_lists_by_title_url(list_title) + "/fields"

    def get_lists_add_field_url(self, list_title):
        return self.get_base_url() + "/GetList(@a1)/Fields/CreateFieldAsXml?@a1='/{}/Lists/{}'".format(
            self.sharepoint_site,
            list_title
        )

    def get_guid_lists_add_field_url(self, list_id):
        return self.get_base_url() + "/lists('{}')/Fields/CreateFieldAsXml".format(
            list_id
        )

    def get_folder_url(self, full_path):
        return self.get_base_url() + "/GetFolderByServerRelativeUrl({})".format(
            self.get_site_path(full_path)
        )

    def get_file_url(self, full_path):
        return self.get_base_url() + "/GetFileByServerRelativeUrl({})".format(
            self.get_site_path(full_path)
        )

    def get_file_content_url(self, full_path):
        return self.get_file_url(full_path) + "/$value"

    def get_move_url(self, from_path, to_path):
        return self.get_file_url(from_path) + "/moveto(newurl={},flags=1)".format(
            self.get_site_path(to_path)
        )

    def get_site_path(self, full_path):
        return "'/{}/{}{}'".format(self.sharepoint_site, self.sharepoint_root, full_path)

    def get_add_folder_url(self, full_path):
        return self.get_base_url() + "/Folders/add('{}/{}')".format(
            self.sharepoint_root,
            full_path
        )

    def get_file_add_url(self, full_path, file_name):
        return self.get_folder_url(full_path) + "/Files/add(url='{}',overwrite=true)".format(file_name)

    @staticmethod
    def assert_login_details(required_keys, login_details):
        if login_details is None or login_details == {}:
            raise SharePointClientError("Login details are empty")
        for key in required_keys:
            if key not in login_details.keys():
                raise SharePointClientError(required_keys[key])

    def assert_response_ok(self, response, no_json=False):
        status_code = response.status_code
        if status_code >= 400:
            enriched_error_message = self.get_enriched_error_message(response)
            if enriched_error_message is not None:
                raise SharePointClientError("Error: {}".format(enriched_error_message))
        if status_code == 400:
            raise SharePointClientError("{}".format(response.text))
        if status_code == 404:
            raise SharePointClientError("Not found. Please check tenant, site type or site name.")
        if status_code == 403:
            raise SharePointClientError("Forbidden. Please check your account credentials.")
        if not no_json:
            self.assert_no_error_in_json(response)

    @staticmethod
    def get_enriched_error_message(response):
        try:
            json_response = response.json()
            enriched_error_message = json_response.get("error").get("message").get("value")
            return enriched_error_message
        except Exception as error:
            logger.info("Error trying to extract error message :{}".format(error))
            return None

    @staticmethod
    def assert_no_error_in_json(response):
        if len(response.content) == 0:
            raise SharePointClientError("Empty response from SharePoint. Please check user credentials.")
        json_response = response.json()
        if "error" in json_response:
            if "message" in json_response["error"] and "value" in json_response["error"]["message"]:
                raise SharePointClientError("Error: {}".format(json_response["error"]["message"]["value"]))
            else:
                raise SharePointClientError("Error: {}".format(json_response))


class SharePointSession():

    def __init__(self, sharepoint_user_name, sharepoint_password, sharepoint_tenant, sharepoint_site, sharepoint_access_token=None):
        self.sharepoint_tenant = sharepoint_tenant
        self.sharepoint_site = sharepoint_site
        self.sharepoint_access_token = sharepoint_access_token

    def get(self, url, headers=None, params=None):
        headers = {} if headers is None else headers
        headers["accept"] = DSSConstants.APPLICATION_JSON
        headers["Authorization"] = self.get_authorization_bearer()
        return requests.get(url, headers=headers, params=params)

    def post(self, url, headers=None, json=None, data=None):
        headers = {} if headers is None else headers
        headers["accept"] = DSSConstants.APPLICATION_JSON
        headers["Authorization"] = self.get_authorization_bearer()
        return requests.post(url, headers=headers, json=json, data=data)

    def get_authorization_bearer(self):
        return "Bearer {}".format(self.sharepoint_access_token)


class LocalSharePointSession():

    def __init__(self, sharepoint_user_name, sharepoint_password, sharepoint_origin, sharepoint_site, sharepoint_access_token=None, ignore_ssl_check=False):
        self.form_digest_value = None
        self.sharepoint_origin = sharepoint_origin
        self.sharepoint_site = sharepoint_site
        self.ignore_ssl_check = ignore_ssl_check
        self.sharepoint_access_token = sharepoint_access_token
        self.sharepoint_user_name = sharepoint_user_name
        self.sharepoint_password = sharepoint_password
        self.auth = HttpNtlmAuth(sharepoint_user_name, sharepoint_password)

    def get(self, url, headers=None, params=None):
        headers = {} if headers is None else headers
        headers["accept"] = DSSConstants.APPLICATION_JSON
        args = {
            "headers": headers,
            "auth": self.auth
        }
        if params is not None:
            args.update({"params": params})
        if self.ignore_ssl_check is True:
            args["verify"] = False
        return requests.get(url, **args)

    def post(self, url, headers=None, json=None, data=None):
        headers = {} if headers is None else headers
        headers["accept"] = DSSConstants.APPLICATION_JSON
        form_digest_value = self.get_form_digest_value()
        if form_digest_value is not None:
            headers["X-RequestDigest"] = form_digest_value
        args = {
            "headers": headers,
            "json": json,
            "data": data,
            "auth": self.auth
        }
        if self.ignore_ssl_check is True:
            args["verify"] = False
        return requests.post(url, **args)

    def get_form_digest_value(self):
        if self.form_digest_value is not None:
            return self.form_digest_value
        headers = {}
        headers["accept"] = DSSConstants.APPLICATION_JSON
        args = {
            "headers": headers,
            "auth": self.auth
        }
        if self.ignore_ssl_check is True:
            args["verify"] = False
        response = requests.post(self.get_context_info_url(), **args)
        self.assert_response_ok(response)
        try:
            json_response = response.json()
            return get_from_json_path(["d", "GetContextWebInformation", "FormDigestValue"], json_response)
        except ValueError:
            return None
        except KeyError:
            return None
        return None

    def get_context_info_url(self):
        return "{}/{}/_api/contextinfo".format(
            self.sharepoint_origin, self.sharepoint_site
        )

    def assert_response_ok(self, response):
        if response.status_code >= 400:
            raise SharePointClientError("Error {} : {}".format(
                response.status_code,
                response.content
            ))
