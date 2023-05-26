import requests
import urllib3
import functools
import json

class ApiActions(object):
    def __init__(self):
        # Suppress warnings 
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.rs = requests.Session()
        
        # Shim requests function to include timeout and ignore SSL certificate warnings
        self.rs.request = functools.partial(self.rs.request, timeout=30, verify=False)

        # Session setup
        self.base_url = "https://login.eagleeyenetworks.com"

    def login(self, username: str, password: str):
        # Define Payload and POST
        payload = {"username": username, "password": password}
        response = self.rs.post(self.base_url + "/g/aaa/authenticate", data = payload)
        assert response.status_code == 200

        # Define payload and authenticate token
        payload = {"token": response.json()['token']}
        response = self.rs.post(self.base_url + "/g/aaa/authorize", data = payload)
        assert response.status_code == 200

        # Set auth_key
        self.auth_key = response.cookies['auth_key']

        # Set user object data
        self.user_object = response.json()

        # Update base URL with active subdomain
        self.base_url = self.base_url.replace('login', self.user_object['active_brand_subdomain'])
        print(self.base_url)

        return self.rs
    
    def get_list_bridges(self):
        # Create bridges list
        bridges = []

        # Make GET request to retrieve list of devices
        response = self.rs.get(self.base_url + "/g/device/list")

        # Deserialize response text to a list object
        data = json.loads(response.text)

        # Loop through and append devices that bridges to the bridges list
        for i in data:
            if i[3] == 'bridge':
                bridges.append(i)

        # Loop through bridge to get and print some values
        for bridge in bridges:
            esn = bridge[1]
            name = bridge[2]
            guid = bridge[8]
            print(f'ESN: {esn} | Name: {name} | GUID: {guid}')

if __name__ == '__main__':
    api = ApiActions()
    api.login("username","password")
    api.get_list_bridges()
