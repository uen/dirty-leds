import lib.bottle as bottle
import json
import numpy

@bottle.route("/", method='GET')
def process():
	return bottle.static_file('index.html', root="static")

@bottle.route("/static/<filepath:path>", method='GET')
def process(filepath):
    return bottle.static_file(filepath, root="static")

def setVis(vis):
	global _vis
	_vis = vis

def setConfig(config):
	global _config;
	_config = config

def setSP(sp):
	global _sp
	_sp = sp

@bottle.route('/api/get/devices', method = 'GET')
def process():
	devices = []
	for device, details in _config.settings["devices"].items():

		effects = {"reactive":[], "nreactive":[]}

		for effect, details in _vis[device].effects.items():
		
			effects_config = _vis[device].dynamic_effects_config[effect]
			options = []
			for effect_config_ in effects_config:
				option = {
					"k": effect_config_[0],
					"name": effect_config_[1],
					"type": effect_config_[2]
				}
				if len(effect_config_) > 3:
					option["config"] = effect_config_[3]
				options.append(option)

			effect_ = {
				"name": effect, 
				"current_options":_config.settings["devices"][device]["effect_opts"][effect],
				"options": options
			}

			if(effect not in _vis[device].non_reactive_effects):
				effects["reactive"].append(effect_)
			else:
				effects["nreactive"].append(effect_)





		devices.append({
			"name":device, 
			"minFrequency":		_config.settings["devices"][device]["configuration"]["MIN_FREQUENCY"],
			"maxFrequency":		_config.settings["devices"][device]["configuration"]["MAX_FREQUENCY"],
			"currentEffect":	_config.settings["devices"][device]["configuration"]["current_effect"], 
			"effects":			effects
		})

	return json.dumps({
		"devices":devices
	})




@bottle.route('/api/set/effect', method = 'GET')
def process():
	foundDevice = None
	foundEffect = None

	device_ = bottle.request.params.device
	effect_ = bottle.request.params.effect
	
	for device, details in _config.settings["devices"].items():
		if(device==device_):
			foundDevice = device

	if(foundDevice is None):
		return json.dumps({"error" : "device not found"})

	for effect, details in _vis[foundDevice].effects.items():
		if(effect == effect_):
			foundEffect = effect

	for effect in _vis[foundDevice].non_reactive_effects:
		if(effect==effect_):
			foundEffect = effect


	if(foundEffect is None):
		return json.dumps({"error": "effect not found"})

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
	_sp[device].create_mel_bank()

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

	_sp[device].create_mel_bank()

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

	for device, details in _config.settings["devices"].items():
		if(device==device_):
			foundDevice = device

	if(foundDevice is None):
		return json.dumps({"error" : "device not found"})

	for effect, details in _vis[foundDevice].effects.items():
		if(effect == effect_):
			foundEffect = effect

	for effect in _vis[foundDevice].non_reactive_effects:
		if(effect==effect_):
			foundEffect = effect

	if(foundEffect is None):
		return json.dumps({"error": "effect not found"})

	for option in _config.settings["devices"][foundDevice]["effect_opts"][foundEffect]:
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

	if isinstance(_config.settings["devices"][foundDevice]["effect_opts"][foundEffect][foundOption], int):
		value_ = int(value_)

	if isinstance(_config.settings["devices"][foundDevice]["effect_opts"][foundEffect][foundOption], numpy.float64):
		value_ = numpty.float64(value_)

	if isinstance(_config.settings["devices"][foundDevice]["effect_opts"][foundEffect][foundOption], float):
		value_ = float(value_)

	_config.settings["devices"][foundDevice]["effect_opts"][foundEffect][foundOption] = value_


	return json.dumps({"status": "ok"})



