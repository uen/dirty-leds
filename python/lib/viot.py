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
        r = requests.get('http://maninet:8888/api/module/verify?uniq='+uniq+"&space="+self.uniq)
        print(r)
        if(not r):
            print('viot: HTTP authentication failure')
            return False

        resp = r.json()
        if(not resp):
            print('viot: HTTP authentication response failure')
            return False

        if (resp['status']=='ok'):
            return resp['data']
        else:
            print("viot: Authentication failure")
            print(resp)
            return False
      