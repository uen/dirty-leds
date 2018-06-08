angular.module('manolisApi', ['ng']).factory('$api',function($http,$location, $rootScope, $timeout){
	var api = {};
	api.fetch = function(url, data, success){ // API library. Fetches from API
		$timeout(function(){
			if(!data) data={};
			
			$http({
				method:'get',
				url:'/api/'+url,
				params:data
			}).success(function(data,status){
				if(data){
					success(data);
				}	
			});
		});
	}
	return api;
})