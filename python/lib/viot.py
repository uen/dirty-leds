


from __future__ import print_function
import numpy as np
import config as config
import lib.melbank as melbank
from scipy.ndimage.filters import gaussian_filter1d
from threading import Thread
import http.client
import time
import sys
import traceback
import json

import requests
from urllib.parse import quote

import paho.mqtt.client as mqtt


mqttClient = mqtt.Client()

defaultOptions = {
	"host": "mqtt.viot.co.uk",
	"port": 1883,
	"debug": True
}

viotState = {}
viotStateListeners = []
def setState(key, value):
	print(f"state{key} set to {value}")

	viotState[key] = value
	for listener in viotStateListeners:
		listener(viotState)

class viotMqtt:
	def __init__(self, options):
		mqttClient.connect(options["host"], options["port"], 60)
		mqttClient.loop_forever()


class viot:
	instance = None
	def __init__(self, options):
		if(not viot.instance):
	   		viot.instance = viot.__viot(options)

	def __getattr__(self, name):
		return getattr(self.instance, name)

	class __viot:
		def __init__(self, options):
			print("viot: Attempting initial connection...")

			mqttClient.on_connect = self.on_connect
			mqttClient.on_message = self.on_message

			options = {**defaultOptions, **options}

			if(not "defaultState" in options):
				print("viot: Called with no defaultState!")

			self.viotState = options["defaultState"]
			self.options = options
			self.listeners = {}
			

		def update_state(self, state):
			mqttClient.publish(self.emitTopic, json.dumps({
				"command": "state",
				"message": state
			}))


		def on(self, command, callback):
			if(not command in self.listeners):
				self.listeners["command"] = []

			self.listeners["command"].append(callback)


		def begin(self, options):
			if(options):
				self.options = {**self.options, **options}

			self.emitTopic = f"device/{self.options['apikey']}/emit"

			mqttThread = Thread(target=viotMqtt, args=[self.options])
			mqttThread.daemon = True
			mqttThread.start()

		def action(self, actionName):
			def wrapper(func):
				if(not actionName in self.listeners):
					self.listeners[actionName] = []

				self.listeners[actionName].append(func)
			return wrapper

		def on_connect(self, a, b, c, d):
			print("viot: Connection established")
			mqttClient.subscribe(f"device/{self.options['apikey']}/receive")
			result = mqttClient.publish(self.emitTopic, json.dumps({"command": "connect"}))

		def on_status(self, payload):
			if(self.options["debug"]):
				print("viot: Received status call")

			mqttClient.publish(self.emitTopic, json.dumps({"command": "status", "message": "online"}))

		def get_template():
			print("viot: get_template() not replaced")

		def set_template(self, templateFunc):
			self.get_template = templateFunc

		def on_template(self, payload):
			if(self.options["debug"]):
				print("viot: Responding to template request")

			template = self.get_template()
			mqttClient.publish(self.emitTopic, json.dumps({
				"command": "template",
				"message": {
					"template": json.dumps(template),
					"state": self.viotState
				}
			}))

		def on_action(self, payload):
			if(self.options["debug"]):
				print(f"viot: Received command {payload['command']} with value: {payload['value']}")


		def on_message(self, client, userdata, message):
			commands = {
				"status" : self.on_status,
				"template" : self.on_template
			}

			try:
				messageData = json.loads(message.payload)
				if(not messageData["command"]):
					print("viot: Received message with no command parameter")
					return False

				if(messageData["command"] in commands):
					commands[messageData["command"]](messageData)
					return

				if(not messageData["command"] in self.listeners):
					print(f"viot: Received unhandled command: {messageData['command']}")

				for callback in self.listeners[messageData["command"]]:
					callback(messageData["value"])

			except ValueError as e:
				print("viot: Invalid message received")
				return False

			except Exception as ex:
				print("error")
				traceback.print_stack()
				print(ex)
				print("fs")



