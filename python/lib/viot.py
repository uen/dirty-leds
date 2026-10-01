from threading import Thread
import traceback
import json

import paho.mqtt.client as mqtt


mqttClient = mqtt.Client()

defaultOptions = {
	"host": "mqtt.viot.co.uk",
	"port": 1883,
	"debug": True
}

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

			except Exception:
				traceback.print_exc()
