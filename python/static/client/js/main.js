var App = angular.module("manolisApp", ['manolisApi'])

App.controller('mainController', function($scope,$rootScope,$location, $api, $timeout, $window){
	$scope.brightness = 1
	$scope.getDevices = () => {
		$api.fetch('get/devices', {}, (data) => {
			if(data.devices){
				$scope.devices = data.devices

				$scope.devices.push(
					Object.assign({...data.devices[0]}, {
						name: "All"
					})
				)
			}

			$scope.activeDevice = $scope.devices[0]
			$scope.activeEffectOption = $scope.activeDevice.effects.reactive[0]
		})
	}

	$scope.toggleSync = () => {
		$scope.synced = !$scope.synced
		$api.fetch('set/sync', {sync:$scope.synced}, (data) => {

		})

	}

	$scope.getSync = () => {
		$api.fetch('get/sync', {}, (data) => {
			console.log(data.sync)
			$scope.synced = data.sync
		})
	}

	$scope.setEffect = (effect) => {
		console.log(effect)
		$api.fetch('set/effect', {device:$scope.activeDevice.name, effect:effect.name}, (data) => {
			if(data.status=='ok'){
				$scope.activeDevice.currentEffect = effect.name
			}
		})
	}

	$scope.setDevice = (device) => {
		$scope.activeDevice = device
	}

	$scope.setBrightness = (brightness) => {
		$api.fetch('set/brightness', {brightness}, (data) => {

		})
	}


	$scope.getBrightness = () => {
		$api.fetch('get/brightness', {}, (data) => {
			$scope.brightness = data.brightness
		})
	}


	$scope.setMaxFrequency = (freq) => {
		freq = parseInt(freq)
		if($scope.activeDevice.minFrequency>=freq)
			return $scope.activeDevice.minFrequency = freq

		$api.fetch('set/frequency/max', {value:freq, device:$scope.activeDevice.name}, () => {})
	}

	$scope.setMinFrequency = (freq) => {
		freq = parseInt(freq)
		if($scope.activeDevice.maxFrequency<=freq){
			return $scope.activeDevice.maxFrequency = freq
		}

		$api.fetch('set/frequency/min', {value:freq, device:$scope.activeDevice.name}, () => {})
	}

	$scope.activeStatus = (device) => {
		return $scope.activeDevice.name == device.name
	}

	$scope.setOption = (key, value) => {
		console.log(key + ' set to ', value)
		$api.fetch('set/option', {
			device: $scope.activeDevice.name,
			effect: $scope.activeEffectOption.name,
			option: key,
			value: JSON.stringify({value: value})
		}, (data) => {})
	}

	$scope.optionActiveStatus = (effect) => {
		return $scope.activeEffectOption.name == effect.name
	}

	$scope.setActiveOption = (option) => {
		$scope.activeEffectOption = option
	}
})