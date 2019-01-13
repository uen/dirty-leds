from __future__ import print_function
import numpy as np
import config as config
import lib.melbank as melbank
from scipy.ndimage.filters import gaussian_filter1d



import requests
from urllib.parse import quote


class viot:
    uniq = ''
    def __init__(self, uniq):
        self.uniq = uniq
    def auth(self, authKey):
        print(self.uniq + "is self uniq")
        print("auth key is ", authKey)
        uniq = quote(self.uniq, safe='')
        authKey = quote(authKey, safe='')
        r = requests.get('http://maninet/api/module/verify?uniq='+uniq+"")
        if(not r):
            print('viot: HTTP authentication failure')
            return False

        resp = r.json()
        if(not resp):
            print('viot: HTTP authentication response failure')
            return False

        if(data.status=='ok'):
            return data.data
        else:
            print("viot: Authentication failure")
            return False
      