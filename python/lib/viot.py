from __future__ import print_function
import numpy as np
import config as config
import lib.melbank as melbank
from scipy.ndimage.filters import gaussian_filter1d
from threading import Thread
import http.client
import time
import socketio



import requests
from urllib.parse import quote

apiKey = 'c9a8c01edd3148fac2f5b97732d07696'
module = 'dirty-leds'



## need something to pick if to use bridge or not here???


actionHandlers = {}
sio = socketio.Client(engineio_logger=True, logger=True, reconnection=True, reconnection_delay=5) 


class viotSocket:
    wsUrl = ''
    def __init__(self, url):
        self.wsUrl = url

        sio.connect(url)
        sio.wait()

    
    @sio.on('connect')
    def on_connect():
        print('viot: Connection established')


    @sio.on('action')
    def on_action(data):
        print('viot: action')
        if not ('request' in data and 'action' in data and 'data' in data):
            print('viot: Received invalid request ID')
            return

        if(data['action'] in actionHandlers):
            res = actionHandlers[data['action']](data['data'])
            if(isinstance(res, str)):
                sio.emit('response', {'request' : data['request'], 'status' : 'failure', 'message' : res})

                return
            sio.emit('response', {'request' : data['request'], 'status' : 'ok', 'data' : res})
        else:
            sio.emit('response', {'request' : data['request'], 'status' : 'failure', 'message' : 'Action handler not found'})

    @sio.on('disconnect')
    def on_disconnect():
        print('disconnected from server')

    def ping():
        print('pinging...')

class viot:
    instance = None
    def __init__(self, uniq):
        print('we are here')
        if(not viot.instance):
            viot.instance = viot.__viot(uniq)
        
    def __getattr__(self, name):
        return getattr(self.instance, name)

    class __viot:

        uniq = ''
        connected = False
        def __init__(self, uniq):
            self.uniq = uniq
            print('viot: Attempting to connect to https://viot.uk')
            
            while self.connected == False:
                authUrl = 'https://viot.uk/api/bridge/auth?apikey={apikey}&uniq={uniq}&module={module}'.format(apikey = apiKey, uniq = uniq, module = module)
                r = requests.get(authUrl)
                if(not r):
                    print('viot: Could not establish connection with server. Retrying in 5s...')
                    time.sleep(5)
                    continue

                resp = r.json()
                if(not resp):
                    print('viot: Invalid response from server. Retrying in 5s...')
                    time.sleep(5)
                    continue

                self.connected = True
                if(resp['status']=='ok'):
                    print('viot: Authorized successfully')
                    self.beginSocket(resp['data']['socket'], resp['data']['authkey'])
                else:
                    print("viot: "+resp['message'])
                    exit()

                    return
        
        def beginSocket(self, url, authKey):
            socketThread = Thread(target=viotSocket, args=[url + "?uniq="+self.uniq+"&authkey="+authKey])
            socketThread.daemon = True
            socketThread.start()

        def action(self, actionName):
            def wrapper(func):
                actionHandlers[actionName] = func
            return wrapper

