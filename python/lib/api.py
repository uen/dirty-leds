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



def validateInput(value, schema=None):

	try:
		validate_structure(value, schema=schema)
	except Exception as error:
		return str(error)

vi = validateInput

def setBoards(boards):
	global _boards;
	_boards = boards

def setConfig(config):
	global _config;
	_config = config;


@viot.action('get/devices')
def process(data):
	devices = []
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

	return {"devices" : devices}



@viot.action('get/brightness')
def process(data):
	return {"brightness" : _config.settings["brightness"]}

@viot.action('set/brightness')
def process(data):
	ve = vi(data, schema={
		'brightness': validate_float(min_value=0.0, max_value=1.0)
	})
	if(ve): return ve

	_config.settings["brightness"] = numpy.float64(data['brightness'])
	return True

	
@viot.action('set/sync')
def process(data):
	ve = vi(data, schema={
		'sync': validate_bool()
	})
	if(ve): return ve
	_config.settings["sync"] = data['sync']
	return True

@viot.action('get/sync')
def process(data):
	return {"sync" : _config.settings["sync"]}

@viot.action("set/effect")
def process(data):
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