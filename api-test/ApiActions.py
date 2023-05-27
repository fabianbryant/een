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

        # Loop through and append devices that are bridges to the bridges list
        for i in data:
            if i[3] == 'bridge':
                bridges.append(i)
                
        # Loop through bridge to get and print some values
        for bridge in bridges:
            esn = camera[1]
            name = camera[2]
            guid = camera[8]
            status = camera[4][0][1]
            print(f'ESN: {esn} | Name: {name} | GUID: {guid} | Status: {status}')
                
    def get_list_cameras(self):
        # Create cameras list
        cameras = []
        
        # Make GET request to retrieve list of devices
        response = self.rs.get(self.base_url + "/g/device/list")
        
        # Deserialize response text to a list object
        data = json.loads(response.text)
        
        # Loop through and append devices that are cameras to the cameras list
        for i in data:
            if i[3] == 'camera':
                cameras.append(i)
        
        # Loop through camera to get and print some values
        for camera in cameras:
            esn = camera[1]
            name = camera[2]
            guid = camera[8]
            status = camera[4][0][1]            
            print(f'ESN: {esn} | Name: {name} | GUID: {guid} | Status: {status}')
            
    def add_bridge(self, name: str, connectID, str):
        # Define payload and PUT
        payload = {"name": name, "connectID": connectID}
        response = self.rs.put(self.base_url + "/g/device", data = payload)
        assert response.status_code == 200
        
    def delete_bridge(self, ID: str):
        # Define payload and DELETE
        payload = {"id": ID}
        response = self.rs.delete(self.base_url + "/g/device", data = payload)
        assert response.status_code == 200

if __name__ == '__main__':
    api = ApiActions()
    api.login("username","password")
    api.get_list_bridges()
    api.get_list_cameras()
