from __future__ import print_function
import numpy as np
import config as config
import lib.melbank as melbank
from scipy.ndimage.filters import gaussian_filter1d
from threading import Thread
import http.client
import time
import sys
import socketio



import requests
from urllib.parse import quote

module = 'dirty-leds'



## need something to pick if to use bridge or not here???


actionHandlers = {}
sio = socketio.Client(reconnection=True, reconnection_delay=5) 


class viotSocket:
    wsUrl = ''
    def __init__(self, url):
        self.wsUrl = url

        sio.connect(url)
    
    @sio.on('connect')
    def on_connect():
        print('viot: Socket established')


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


    @sio.on('device-connected')
    def on_device_connected(data):
        if not ('request' in data):
            print('viot: Device connection requested but no device data')
            sio.emit('response', {'request' : data['request'], 'status' : 'failure', 'message' : 'invalid.request'})
            return

        sio.emit('response', {'request' : data['request'], 'status' : 'ok', 'data' : '{}'})


    @sio.on('disconnect')
    def on_disconnect():
        print('viot: Socket disconnected')
        auth = viot.instance.auth()
        url = auth['socket'] + "?uniq="+viot.instance.uniq+"&authkey="+auth['authkey']
        sio.connection_url = url



def getAuth(apiKey, module, uniq):
    authUrl = 'https://viot.uk/api/bridge/auth?apikey={apikey}&uniq={uniq}&module={module}'.format(apikey = apiKey, uniq = uniq, module = module)
    r = requests.get(authUrl)
    if(not r):
        print('viot: Could not establish connection with server. Retrying in 5s...')
        return False

    resp = r.json()
    if(not resp):
        print('viot: Invalid response from server. Retrying in 5s...')
        return False
    return resp


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
            print('viot: Attempting initial connection to https://viot.uk')

            resp = self.auth()
            self.beginSocket(resp['socket'], resp['authkey'])
        
        def beginSocket(self, url, authKey):
            socketThread = Thread(target=viotSocket, args=[url + "?uniq="+self.uniq+"&authkey="+authKey])
            socketThread.daemon = True
            socketThread.start()

        def action(self, actionName):
            def wrapper(func):
                actionHandlers[actionName] = func
            return wrapper

        def auth(self):
            self.connected = False
            while self.connected == False:
                resp = getAuth(apiKey, module, self.uniq)
                if(not resp):
                    time.sleep(5)
                    continue

                self.connected = True
                if(resp['status']=='ok'):
                    print('viot: Authorized successfully')
                    return { 'socket' : resp['data']['socket'], 'authkey' : resp['data']['authkey']}
                else:
                    print("viot: "+resp['message'])
                    exit()
                return