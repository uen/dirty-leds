


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
		print("ziajdiowajido")
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
			print("viot: attempting initial qmtt connection")

			mqttClient.on_connect = self.on_connect
			mqttClient.on_message = self.on_message

			options = {**defaultOptions, **options}

			if(not "defaultState" in options):
				print("viot: Called with no defaultState!")

			self.viotState = options["defaultState"]

			if(not "apiKey" in options):
				print("viot: Called with no apiKey!")

			self.options = options

			self.listeners = {}

			self.emitTopic = f"device/{self.options['apikey']}/emit"



			self.beginMqtt(options)

		def update_state(self, state):
			print("new state")
			print(state)
			mqttClient.publish(self.emitTopic, json.dumps({
				"command": "state",
				"message": state
			}))


		def on(self, command, callback):
			if(not command in self.listeners):
				self.listeners["command"] = []

			self.listeners["command"].append(callback)


		def beginMqtt(self, options):
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
			print(f"device/{self.options['apikey']}/receive")

			mqttClient.publish(self.emitTopic, json.dumps({"command": "connect"}))


		def on_status(self, payload):
			if(self.options["debug"]):
				print("viot: Received status call")

			mqttClient.publish(self.emitTopic, json.dumps({"command": "status", "message": "online"}))

		def get_template():
			print("get template not repalced")

		def set_template(self, templateFunc):
			self.get_template = templateFunc

		def on_template(self, payload):
			if(self.options["debug"]):
				print("viot: Responding to template request")


			print("getting template")

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
			print("got a message")
			print(message.topic)
			print(message.payload)

			commands = {
				"status" : self.on_status,
				"template" : self.on_template
			}

			try:
				print("trying")
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
				print("invalid message")
				return False

			except Exception as ex:
				print("error")
				traceback.print_stack()
				print(ex)
				print("fs")



