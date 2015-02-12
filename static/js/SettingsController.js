var app = angular.module('AutomationTools', []);

app.config(['$interpolateProvider', function($interpolateProvider) {
  $interpolateProvider.startSymbol('[[');
  $interpolateProvider.endSymbol(']]');
}]);

app.controller('SettingsController', function($scope, $http){
	$scope.show_message = false;
  //получаем параметры приложения
  $http.get('/mainsettings/get').success(function(data, status, headers, config) {
      $scope.settings = data;
  }).error(function(data, status, headers, config) { });

  $scope.saveSettings = function(settings) {
  	if(settings.password == null) 
  	    password = "";
    else
        password = settings.password;
    var data = { "username":       settings.username,
                 "password":       password,
                 "bamboo_url":     settings.bamboo_url,
                 "jira_url":       settings.jira_url,
                 "confluence_url": settings.confluence_url };

    $http.post('/mainsettings/save', data).success(function(data, status, headers, config) {
        $scope.settings = data;
	    $scope.show_message = true;
    }).error(function(data, status, headers, config) { });
  }
  
});