import lib.bottle as bottle
import json
import numpy

@bottle.route("/", method='GET')
def process():
	return bottle.static_file('index.html', root="static")

@bottle.route("/static/<filepath:path>", method='GET')
def process(filepath):
    return bottle.static_file(filepath, root="static")


def setBoards(boards):
	global _boards;
	_boards = boards

def setConfig(config):
	global _config;
	_config = config;


@bottle.route('/api/get/devices', method = 'GET')
def process():
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

	return json.dumps({
		"devices":devices
	})


@bottle.route('/api/sync', method = 'GET')
def process():
	_config.settings["sync"] = bottle.request.params.sync

@bottle.route('/api/set/effect', method = 'GET')
def process():
	foundDevice = None
	foundEffect = None

	device_ = bottle.request.params.device
	effect_ = bottle.request.params.effect
	useAll_ = bottle.request.params.device == "All"
	
	for device, details in _config.settings["devices"].items():
		if(device==device_):
			foundDevice = device

	if(foundDevice is None):

		return json.dumps({"error" : "device not found"})

	for effect, details in _boards[foundDevice].visualizer.effects.items():
		if(effect == effect_):
			foundEffect = effect

	for effect in _boards[foundDevice].visualizer.non_reactive_effects:
		if(effect==effect_):
			foundEffect = effect


	if(foundEffect is None):
		return json.dumps({"error": "effect not found"})

	if useAll_:
		for device in _config.settings["devices"]:
			print(device)
			_config.settings["devices"][device]["configuration"]["current_effect"] = foundEffect
	else:		
		_config.settings["devices"][device]["configuration"]["current_effect"] = foundEffect

	return json.dumps({"status": "ok"})





@bottle.route('/api/set/frequency/max', method = 'GET')
def process():
	foundDevice = None
 	
	device_ = bottle.request.params.device
	value_ = bottle.request.params.value

	if(value_ is None):
		return json.dumps({"error" : "invalid value"})

	for device, details in _config.settings["devices"].items():
		if(device==device_):
			foundDevice = device

	if(foundDevice is None):
		return json.dumps({"error" : "device not found"})

	value_ = int(value_)


	_config.settings["devices"][device]["configuration"]["MAX_FREQUENCY"] = value_
	_boards[device].signalProcessor.create_mel_bank()

	return json.dumps({"status": "ok"})




@bottle.route('/api/set/frequency/min', method = 'GET')
def process():
	foundDevice = None
 	
	device_ = bottle.request.params.device
	value_ = bottle.request.params.value

	if(value_ is None):
		return json.dumps({"error" : "invalid value"})

	for device, details in _config.settings["devices"].items():
		if(device==device_):
			foundDevice = device

	if(foundDevice is None):
		return json.dumps({"error" : "device not found"})

	value_ = int(value_)

	_boards[device].signalProcessor.create_mel_bank()

	_config.settings["devices"][device]["configuration"]["MIN_FREQUENCY"] = value_

	return json.dumps({"status": "ok"})


@bottle.route('/api/set/option', method = 'GET')
def process():
	foundDevice = None
	foundEffect = None
	foundOption = None


	device_ = bottle.request.params.device
	effect_ = bottle.request.params.effect
	option_ = bottle.request.params.option
	value_ = bottle.request.params.value
	useAll_ = device_ == "All"

	for device, details in _config.settings["devices"].items():
		if(device==device_):
			foundDevice = device

	if(foundDevice is None):
		return json.dumps({"error" : "device not found"})

	for effect, details in _boards[foundDevice].visualizer.effects.items():
		if(effect == effect_):
			foundEffect = effect

	if(foundEffect is None):
		return json.dumps({"error": "effect not found"})

	for option in _boards[foundDevice].effectConfig[foundEffect]:
		if(option==option_):
			foundOption = option

	if(foundOption is None):
		return json.dumps({"error": "effect option not found"})

	# Needs code adding to check the value type is correct


	try:
		value = json.loads(value_)
		value_ = value["value"]
	except Exception as e:
		return json.dumps({"error": "invalid value"})

	if isinstance(_boards[foundDevice].effectConfig[foundEffect][foundOption], int):
		value_ = int(value_)

	if isinstance(_boards[foundDevice].effectConfig[foundEffect][foundOption], numpy.float64):
		value_ = numpty.float64(value_)

	if isinstance(_boards[foundDevice].effectConfig[foundEffect][foundOption], float):
		value_ = float(value_)

	if useAll_:
		for device in _config.settings["devices"]:
			_boards[device].effectConfg[foundEffect][foundOption] = value_
	else:
		_boards[foundDevice].effectConfig[foundEffect][foundOption] = value_

	return json.dumps({"status": "ok"})