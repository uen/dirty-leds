import json
import numpy
import os
import re
import glob
from .vendor.validation import (
	validate_int,
	validate_float,
	validate_structure,
	validate_bool,
	validate_text
)
from .viot import viot as viot_

# Initial state is set when get_template is called
state = {}

viot = viot_({
    "defaultState": state
})

# Reload state
def reload_state():
	devices, effects = get_devices_effects()

	tabs = []
	for device in devices:
		for effect in device["effects"]["reactive"] + device["effects"]["nreactive"]:
			effectOptionContent = []
			for option in effect["options"]:
				state[f"OPTION/{device['name']}/{effect['name']}/{option['k']}"] = effect["current_options"][option["k"]]


		# Update state with the current effect
		state[f"CURRENT_EFFECT/{device['name']}"] = device["currentEffect"]

	# Set brightness and sync in state
	state[f"BRIGHTNESS"] = _config.settings["brightness"] * 100
	state[f"SYNC"] = _config.settings["sync"]
	state[f"CURRENT_PROFILE"] = _config.settings["currentProfile"]
	state[f"SAVE_PROFILE_VISIBLE"] = state[f"CURRENT_PROFILE"] == ""
	state[f"DELETE_PROFILE_VISIBLE"] = state[f"CURRENT_PROFILE"] != ""

	viot.update_state(state)
	
# Change the state to custom once something has been changed
def setCustomProfile():
	state[f"DELETE_PROFILE_VISIBLE"] = False
	state[f"SAVE_PROFILE_VISIBLE"] = True
	state[f"CURRENT_PROFILE"] = ""

# Generate control panel template for viot
def get_template():
	devices, effects = get_devices_effects()

	mainTabs = []
	deviceTabs = []
	deviceEffectSections = []

	for device in devices:
		nonReactiveButtons = []
		reactiveButtons = []
		effectOptionTabs = []

		# Generate profile buttons

		get_profile_buttons()

		
		
		# Generate non reactive effect buttons
		for effect in device["effects"]["nreactive"]:
			nonReactiveButtons.append({
				"label": effect["name"],
				"value": effect["name"],
				"data": {
					"device": device["name"],
					"effect": effect["name"]
				},
			})

		# Generate reactive effect buttons
		for effect in device["effects"]["reactive"]:
			reactiveButtons.append({
				"label": effect["name"],
				"value": effect["name"],
				"data": {
					"device": device["name"],
					"effect": effect["name"]
				},
			})

		# Generate effect option tabs
		for effect in device["effects"]["reactive"] + device["effects"]["nreactive"]:
			effectOptionContent = []
			for option in effect["options"]:
				sectionContent = []

				# Sliders
				if(option["type"] == "float_slider" or option["type"] == "slider"):
					sectionContent.append({
						"type": "slider",
						"action": "set-option",
						"state": f"OPTION/{device['name']}/{effect['name']}/{option['k']}",
						"data": {"device": device['name'], "effect": effect['name'], "option": option['k']},
						"min": option["config"][0],
						"max": option["config"][1],
						"step": option["config"][2]
					})




				# Dropdowns
				if(option["type"] == "dropdown"):
					settingOptions = []
					for settingOption in option["config"]:
						settingOptions.append({
                        	"label": settingOption,
                        	"value": settingOption
                        })

					sectionContent.append({
						"type": "select",
						"action": "set-option",
						"state": f"OPTION/{device['name']}/{effect['name']}/{option['k']}",
						"data": {"device": device['name'], "effect": effect['name'], "option": option['k']},
						"options": settingOptions
					})

				# Checkboxes
				if(option["type"] == "checkbox"):
					sectionContent.append({
						"type": "checkbox",
						"action": "set-option",
						"state": f"OPTION/{device['name']}/{effect['name']}/{option['k']}",
						"data": {"device": device['name'], "effect": effect['name'], "option": option['k']},
					})


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

		# Add tab effect section
		deviceEffectSections.append({
			"type": "section",
			"label": device['name'],
			"content": [
			# 	{
			# 				"type": "button-toggle-bar",
			# 				"color": "info",
			# 				"rounded": True,
			# 				"action": "set-effect",
			# 				"state": f"CURRENT_EFFECT/{device['name']}",
			# 				"buttons": nonReactiveButtons
			# 			}
			# ]
			# [
				{
					"type": "columns",
					"content": [
						{
							"type": "column",
							"size": 6,
							"content": [{
								"type": "button-toggle-bar",
								"color": "info",
								"rounded": True,
								"action": "set-effect",
								"state": f"CURRENT_EFFECT/{device['name']}",
								"buttons": nonReactiveButtons
							}],
						},
						{
							"type": "column",
							"size": 6,
							"content": [{
								"type": "button-toggle-bar",
								"color": "info",
								"rightAlign": True,
								"rounded": True,
								"action": "set-effect",
								"state": f"CURRENT_EFFECT/{device['name']}",
								"buttons": reactiveButtons
							}]
						}
					]
				}
			]
		})

		# Add a tab per device
		deviceTabs.append({
			"label": device["name"],
			"type" : "tab",
			"content" : [
				{
					"type": "section",
					"label": "Non-reactive effects",
					"content": [
						{
							"type": "button-toggle-bar",
							"color": "info",
							"rounded": True,
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
							"color": "info",
							"rounded": True,
							"action": "set-effect",
							"state": f"CURRENT_EFFECT/{device['name']}",
							"buttons": reactiveButtons
						}
					]
				},
				{
					"type": "tabs",
					"subtype": "secondary",
					"content": effectOptionTabs
				}
			]
		})

	mainTabs.append({
		"label": "Overview",
		"type": "tab",
		"content" : [
			{
				"type": "section",
				"label": "Profiles",
				"buttons": [
					{
						"label": "Save profile",
						"action": "open-modal",
						"value": "save-profile",
						"visibleState": "SAVE_PROFILE_VISIBLE"
					},
					{
						"label": "Delete profile",
						"action": "delete-profile",
						"visibleState": "DELETE_PROFILE_VISIBLE"
					}
				],
				"content": [
					{
						"type": "button-toggle-bar",
						"fromState": "PROFILE_BUTTONS",
						"color": "warning",
						"rounded": True,
						"action": "set-profile",
						"state": f"CURRENT_PROFILE"
					}
				],
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
			*deviceEffectSections
		]
	})

	mainTabs.append({
		"label": "Options",
		"type": "tab",
		"content": [
			{
				"type": "tabs",
				"subtype": "secondary",
				"inTab": True,
				"content": deviceTabs
			}
		]
	})

		# Add sync toggle button
	mainTabs.append({
		"label": "Sync",
		"type": "tab",
		"toggleable": True,
		"action": "set-sync",
		"state": "SYNC"
	})

	reload_state()

	# Return the template
	return {
		"orientation": "landscape",
		"control" : [
			{
				"type": "tabs",
				"content": mainTabs
			}
		],
		"modals" : {
			"save-profile": {
				"title": "Save current profile",
				"submitLabel": "Save",
				"action": "save-profile",
				"content": [
					{
						"type": "text",
						"minLength": 1,
						"maxLength": 20,
						"label": "Profile name",
						"description": "The name of your profile",
						"pattern": ".*[a-zA-Z].*",
						"placeholder": "Romantic",
						"name": "name",
						"title": "Profile name - At least one character"
					}
				]
			}
		}
	}


viot.set_template(get_template)

def setConfig(config):
	global _config
	_config = config

	viot.begin({"apikey": config.settings["apikey"]})


def setBoards(boards):
	global _boards
	_boards = boards

def get_profiles():
	profiles = {}
	files = glob.glob("profiles/*.json")
	
	for profile in files:
		fileName = os.path.basename(profile)
		with open(profile, "r") as profileJson:
			profileData = json.load(profileJson)
			profiles[re.sub("\.json", "", fileName)] = profileData

	return profiles

def get_profile_buttons():
	profileButtons = []

	profiles = get_profiles()
	for profile, profileData in profiles.items():
		profileButtons.append({
			"label": profileData["name"],
			"value": profile
		})


	state[f"PROFILE_BUTTONS"] = profileButtons
	return profileButtons	
	

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

def validateInput(value, schema=None):
	try:
		validate_structure(value, schema=schema)
	except Exception as error:
		return str(error)

vi = validateInput


# VIoT APIs

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


	for effect, details in _boards[foundDevice].visualizer.effects.items():
		if(effect == effect_):
			foundEffect = effect
			break

	for effect in _boards[foundDevice].visualizer.non_reactive_effects:
		if(effect==effect_):
			foundEffect = effect
			break

	if(foundEffect is None):
		return "effect not found"

	setCustomProfile()

	if _config.settings["sync"]:
		for device in _config.settings["devices"]:
			_config.settings["devices"][device]["configuration"]["current_effect"] = foundEffect
			state[f"CURRENT_EFFECT/{device}"] = foundEffect
	else:
		_config.settings["devices"][foundDevice]["configuration"]["current_effect"] = foundEffect
		state[f"CURRENT_EFFECT/{foundDevice}"] = foundEffect

	viot.update_state(state)

	return True


@viot.action('set-brightness')
def process(data):
	if(not "value" in data): return
	data = data["value"]
	ve = validate_int(numpy.int(data), min_value=0, max_value=100)
	if(ve): return ve

	setCustomProfile()

	state["BRIGHTNESS"] = numpy.float(data)	
	brightness = numpy.float64(state["BRIGHTNESS"] / 100.0)
	_config.settings["brightness"] = brightness
	
	viot.update_state(state)

	return True

@viot.action('set-sync')
def process(data):
	if not "value" in data: return

	ve = validate_bool(data["value"])
	if(ve): return ve

	setCustomProfile()
	state["SYNC"] = data["value"]
	_config.settings["sync"] = data["value"]
	viot.update_state(state)

	return True

@viot.action("save-profile")
def process(data):
	if(not "data" in data): return
	ve = vi(data["data"], schema={
		"name": validate_text()
	})
	if(ve): return ve

	data["data"]["name"] = re.sub('[^A-Za-z0-9.-]+', "", data["data"]["name"])
	if(len(data["data"]["name"]) <= 0): return

	# Save the current settings state (brightness, sync)
	settings = {
		"brightness": _config.settings["brightness"],
		"sync": _config.settings["sync"]
	}

	# Save the current state of all the devices
	deviceSettings = {}
	for device, details in _config.settings["devices"].items():
		deviceSettings[device] = _boards[device].getProfile()

	# Write the profile to a file
	f = open("./profiles/"+data["data"]["name"].lower()+".json", "w")
	f.write(json.dumps({"name": data["data"]["name"], "settings": settings, "devices": deviceSettings}))
	f.close()

	get_profile_buttons()

	set_profile(data["data"]["name"].lower())
	return True

@viot.action("delete-profile")
def process(data):
	if(not "CURRENT_PROFILE" in state): return
	path = "./profiles/"+state[f"CURRENT_PROFILE"]+".json"
	if(os.path.isfile(path)):
		os.remove(path)

		get_profile_buttons()
		setCustomProfile()
		viot.update_state(state)


def set_profile(profileName):
	path = "./profiles/"+profileName.lower()+".json"

	if(os.path.isfile(path)):
		with open(path, "r") as profileJson:
			profileData = json.load(profileJson)
			
			_config.settings["brightness"] = profileData["settings"]["brightness"]
			_config.settings["sync"] = profileData["settings"]["sync"]
			_config.settings["currentProfile"] = profileName


			state[f"DELETE_PROFILE_VISIBLE"] = True
			state[f"SAVE_PROFILE_VISIBLE"] = False


			for device_, deviceData_ in profileData["devices"].items():
				foundDevice = None
				for device, deviceData in _config.settings["devices"].items():
					if(device==device_):
						foundDevice = device
						break

				if(foundDevice is None): break
				_boards[foundDevice].setProfile(deviceData_)

			reload_state()
	else:
		print("dirty-leds: Tried to load a profile that doesn't exist ("+path+")")


@viot.action("set-profile")
def process(data):
	if(not "value" in data): return
	profileName = re.sub('[^A-Za-z0-9.-]+', "", data["value"])
	set_profile(profileName)
	


@viot.action('set-option')
def process(data):
	if(not "data" in data): return
	if(not "value" in data): return

	ve = vi(data["data"], schema={
		"device" : validate_text(),
		"effect" : validate_text(),
		"option" : validate_text()
	})
	if(ve): return ve

	foundDevice = None
	foundEffect = None
	foundOption = None


	device_ = data['data']['device']
	effect_ = data['data']['effect']
	option_ = data['data']['option']
	value_ = data['value']
	useAll_ = _config.settings["sync"]

	for device, details in _config.settings["devices"].items():
		if(device==device_):
			foundDevice = device
			break


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
			break

	if(foundOption is None):
		return "Effect option not found"

	if isinstance(_boards[foundDevice].effectConfig[foundEffect][foundOption], int):
		value_ = int(value_)

	if isinstance(_boards[foundDevice].effectConfig[foundEffect][foundOption], numpy.float64):
		value_ = numpy.float64(value_)

	if isinstance(_boards[foundDevice].effectConfig[foundEffect][foundOption], float):
		value_ = float(value_)

	setCustomProfile()
	if _config.settings["sync"]:
		for device, details in _config.settings["devices"].items():
			_boards[device].effectConfig[foundEffect][foundOption] = value_
			state[f"OPTION/{device}/{foundEffect}/{foundOption}"] = value_
	else:
		state[f"OPTION/{foundDevice}/{foundEffect}/{foundOption}"] = value_
		_boards[foundDevice].effectConfig[foundEffect][foundOption] = value_

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
			break

	if(foundDevice is None):
		return "Device not found"

	value_ = int(value_)

	setCustomProfile()
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
			break

	if(foundDevice is None):
		return "Device not found"

	value_ = int(value_)

	_boards[device].signalProcessor.create_mel_bank()

	setCustomProfile()
	_config.settings["devices"][device]["configuration"]["MIN_FREQUENCY"] = value_

	return True
