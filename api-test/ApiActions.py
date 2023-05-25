import requests
import urllib3
import functools

class ApiActions(object):
    def __init__(self):
        # Suppress warnings 
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.rs = requests.Session()
        
        # Shim requests funtion to include timeout and ignore SSL certificate warnings
        self.rs.request = functools.partial(self.rs.request, timeout=30, verify=False)

        # Session setup
        self.base_url = "https://login.eagleeyenetworks.com"

if __name__ == '__main__':
    api = ApiActions()
