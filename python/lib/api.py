import json
import numpy
from .vendor.validation import (
	validate_int,
	validate_float,
	validate_structure,
	validate_bool,
	validate_text
)
from .viot import viot as viot_

def setConfig(config):
	global _config
	_config = config


def setBoards(boards):
	global _boards
	_boards = boards

# Initial state is set when get_template is called
state = {}

def get_devices_effects():
	devices = []
	# Add effects and effect options to each devices
	for device, details in _config.settings["devices"].items():
		effects = {"reactive":[], "nreactive":[]}

		for effect, details in _boards[device].visualizer.effects.items():
			currentOptions = None
			options = []
			if effect in _boards[device].visualizer.dynamic_effects_config:
				currentOptions = _boards[device].effectConfig[effect]

				effects_config = _boards[device].visualizer.dynamic_effects_config[effect]

				for effect_config_ in effects_config:
					option = {
						"k": effect_config_[0],
						"name": effect_config_[1],
						"type": effect_config_[2]
					}
					if len(effect_config_) > 3:
						option["config"] = effect_config_[3]
					options.append(option)
			else:
				currentOptions = {}


			effect_ = {
				"name": effect,
				"current_options":currentOptions,
				"options": options
			}

			if(details.nonReactive):
				effects["nreactive"].append(effect_)
			else:
				effects["reactive"].append(effect_)


		devices.append({
			"name":device,
			"minFrequency":		_boards[device].config["MIN_FREQUENCY"],
			"maxFrequency":		_boards[device].config["MAX_FREQUENCY"],
			"currentEffect":	_boards[device].config["current_effect"],
			"effects":			effects
		})

	return devices, effects

# Generate control panel template for viot
def get_template():
	devices, effects = get_devices_effects()

	tabs = []
	for device in devices:
		nonReactiveButtons = []
		reactiveButtons = []
		effectOptionTabs = []

		# Generate non reactive effect buttons
		for effect in effects["nreactive"]:
			print(effect["name"], "device")
			nonReactiveButtons.append({
				"label": effect["name"],
				"value": effect["name"],
				"data": {
					"device": device["name"],
					"effect": effect["name"]
				},
			})

		# Generate reactive effect buttons
		for effect in effects["reactive"]:
			reactiveButtons.append({
				"label": effect["name"],
				"data": {
					"device": device["name"],
					"effect": effect["name"]
				},
			})

		# Generate effect option tabs
		for effect in effects["reactive"] + effects["nreactive"]:
			effectOptionContent = []
			print(effect)
			for option in effect["options"]:
				sectionContent = []

				# Sliders
				if(option["type"] == "float_slider" or option["type"] == "slider"):
					sectionContent.append({
						"type": "slider",
						"action": f"set-option/{device['name']}/{option['k']}",
						"state": "BRIGHTNESS",
						"min": 0,
						"max": 100,
						"step": 10
					})

				# Dropdowns
				if(option["type"] == "dropdown"):
					print("dropdiown not supproted yet")

				# Checkboxes
				if(option["type"] == "checkbox"):
					print("checkbox not supported yet")

				# Create the section and add the options
				effectOptionContent.append({
					"type": "section",
					"label": option["name"],
					"content": sectionContent
				})

			# Add the effect option tab
			effectOptionTabs.append({
				"label": effect["name"],
				"type": "tab",
				"content": effectOptionContent
			})

		# Add a tab per device
		tabs.append({
			"label": device["name"],
			"type" : "tab",
			"content" : [
				{
					"type": "section",
					"label": "Non-reactive effects",
					"content": [
						{
							"type": "button-toggle-bar",
							"rounded": True,
							"color": "info",
							"action": "set-effect",
							"state": f"CURRENT_EFFECT/{device['name']}",
							"buttons": nonReactiveButtons
						}
					]
				},
				{
					"type": "section",
					"label": "Reactive effects",
					"content": [
						{
							"type": "button-toggle-bar",
							"rounded": True,
							"color": "info",
							"action": "set-effect",
							"state": f"CURRENT_EFFECT/{device['name']}",
							"buttons": reactiveButtons
						}
					]
				},
				{
					"type": "section",
					"label": "Brightness",
					"content": [
						{
							"type": "slider",
							"action": "set-brightness",
							"state": "BRIGHTNESS",
							"min": 0,
							"max": 100,
							"step": 10
						}
					]
				},
				#{
				#	"type": "section",
				#	"label": "Minimum Frequency",
				#	"content": [
				#		{
				#			"type": "slider",
				#			"action": "set-min-frequency",
				#			"state": f"MIN-FREQUENCY/{device['name']}",
				#			"min": 0,
				#			"max": 100,
				#			"step": 10
				#		}
				#	]
				#},
				#{
				#	"type": "section",
				#	"label": "Maximum Frequency",
				#	"content": [
				#		{
				#			"type": "slider",
				#			"action": "set-max-frequency",
				#			"state": f"MAX-FREQUENCY/{device['name']}",
				#			"min": 0,
				#			"max": 100,
				#			"step": 10
				#		}
				#	]
				#}
				{
					"type": "tabs",
					"subtype": "secondary",
					"tabs": effectOptionTabs
				}
			]
		})

		# Update state with the current effect
		state[f"CURRENT_EFFECT/{device['name']}"] = device["currentEffect"]

	# Add sync toggle button
	tabs.append({
		"label": "Sync",
		"type": "tab",
		"toggleable": True,
		"action": "set-sync",
		"state": "SYNC"
	})

	# Set brightness and sync in state
	state[f"BRIGHTNESS"] = _config.settings["brightness"] * 100
	state[f"SYNC"] = _config.settings["sync"]

	# Return the template
	return {
		"orientation": "landscape",
		"control" : [
			{
				"type": "tabs",
				"tabs": tabs
			}
		]
	}


viot = viot_({
    "apikey": "69a1ee068d4d0286a0c33c8467a1548cff583dad3a4744d2fca98e053d57b866",
    "defaultState": state
})

viot.set_template(get_template)



def validateInput(value, schema=None):
	try:
		validate_structure(value, schema=schema)
	except Exception as error:
		return str(error)

vi = validateInput




@viot.action('set-effect')
def process(data):
	data = data["data"]
	ve = vi(data, schema={"device" : validate_text(), "effect" : validate_text()})
	if(ve): return ve

	foundDevice = None
	foundEffect = None

	device_ = data['device']
	effect_ = data['effect']

	for device, details in _config.settings["devices"].items():
		if(device==device_):
			foundDevice = device

	if(foundDevice is None):
                                 		return "device not found"

	if(_config.settings["sync"]):
		foundDevice = next(iter(_config.settings["devices"]))


	for effect, details in _boards[foundDevice].visualizer.effects.items():
		if(effect == effect_):
			foundEffect = effect

	for effect in _boards[foundDevice].visualizer.non_reactive_effects:
		if(effect==effect_):
			foundEffect = effect

	if(foundEffect is None):
		return "effect not found"

	if _config.settings["sync"]:
		for device in _config.settings["devices"]:
			_config.settings["devices"][device]["configuration"]["current_effect"] = foundEffect
	else:
		_config.settings["devices"][foundDevice]["configuration"]["current_effect"] = foundEffect

	state[f"CURRENT_EFFECT/{foundDevice}"] = foundEffect
	viot.update_state(state)

	return True


@viot.action('set-brightness')
def process(data):
	print("brightness")
	print(data)
	ve = validate_int(numpy.int(data), min_value=0, max_value=100)
	if(ve): return ve


	print("set brightness 2")


	state["BRIGHTNESS"] = numpy.float(data)
	brightness = numpy.float64(state["BRIGHTNESS"] / 100.0)
	_config.settings["brightness"] = brightness

	viot.update_state(state)

	return True

@viot.action('set-sync')
def process(data):
	ve = validate_bool(data)
	if(ve): return ve

	state["SYNC"] = data
	_config.settings["sync"] = data
	viot.update_state(state)

	return True


@viot.action('set/frequency/max')
def process(data):
	ve = vi(data, schema={"device" : validate_text(), "value" : validate_int(
		max_value=20000,
		min_value=20,
	)})
	if(ve): return ve

	foundDevice = None

	device_ = data['device']
	value_ = data['value']

	for device, details in _config.settings["devices"].items():
		if(device==device_):
			foundDevice = device

	if(foundDevice is None):
		return "Device not found"

	value_ = int(value_)


	_config.settings["devices"][device]["configuration"]["MAX_FREQUENCY"] = value_
	_boards[device].signalProcessor.create_mel_bank()

	return True




@viot.action('set/frequency/min')
def process(data):
	ve = vi(data, schema={"device" : validate_text(), "value" : validate_int(
		max_value=19999,
		min_value=0
	)})
	if(ve): return ve


	device_ = data['device']
	value_ = data['value']

	for device, details in _config.settings["devices"].items():
		if(device==device_):
			foundDevice = device

	if(foundDevice is None):
		return "Device not found"

	value_ = int(value_)

	_boards[device].signalProcessor.create_mel_bank()

	_config.settings["devices"][device]["configuration"]["MIN_FREQUENCY"] = value_

	return True

@viot.action('set/option')
def process(data):
	ve = vi(data, schema={
		"device" : validate_text(),
		"effect" : validate_text(),
		"option" : validate_text(),
		"value"  : validate_text()})
	if(ve): return ve

	foundDevice = None
	foundEffect = None
	foundOption = None


	device_ = data['device']
	effect_ = data['effect']
	option_ = data['option']
	value_ = data['value']
	useAll_ = _config.settings["sync"]

	for device, details in _config.settings["devices"].items():
		if(device==device_):
			foundDevice = device


	if(useAll_):
		foundDevice = next(iter(_config.settings["devices"]))

	if(foundDevice is None):
		return  "Device not found"

	for effect, details in _boards[foundDevice].visualizer.effects.items():
		if(effect == effect_):
			foundEffect = effect

	if(foundEffect is None):
		return "Effect not found"

	for option in _boards[foundDevice].effectConfig[foundEffect]:
		if(option==option_):
			foundOption = option

	if(foundOption is None):
		return "Effect option not found"

	try:
		value = json.loads(value_)
		value_ = value["value"]
	except Exception as e:
		return "Invalid value"


	if isinstance(_boards[foundDevice].effectConfig[foundEffect][foundOption], int):
		value_ = int(value_)

	if isinstance(_boards[foundDevice].effectConfig[foundEffect][foundOption], numpy.float64):
		value_ = numpy.float64(value_)

	if isinstance(_boards[foundDevice].effectConfig[foundEffect][foundOption], float):
		value_ = float(value_)

	if _config.settings["sync"]:
		for device, details in _config.settings["devices"].items():
			_boards[device].effectConfig[foundEffect][foundOption] = value_
	else:
		_boards[foundDevice].effectConfig[foundEffect][foundOption] = value_
	return True