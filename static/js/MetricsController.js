var app = angular.module('AutomationTools', []);

app.config(['$interpolateProvider', function($interpolateProvider) {
  $interpolateProvider.startSymbol('[[');
  $interpolateProvider.endSymbol(']]');
}]);

app.controller('MetricsController', function($scope, $http){

  $scope.selection = [];

  // toggle selection for a given user by name
  $scope.toggleSelection = function toggleSelection(userName) {
    var idx = $scope.selection.indexOf(userName);
    // is currently selected
    if (idx > -1)
      $scope.selection.splice(idx, 1);
    // is newly selected
    else
      $scope.selection.push(userName);
  };

	$scope.show_message = false;

  function getUsers() {
    $http.get('/metrics/users').success(function(data, status, headers, config) {
      $scope.users = data;
      for(var i = 0; i < $scope.users.length; ++i) {
        $scope.toggleSelection($scope.users[i].name);
      }
    }).error(function(data, status, headers, config) { });
  }

  //получаем список пользователей
  getUsers();
  
  // добавление пользователя
  $scope.addUser = function(user) {
    var data = { "username":       user.name }
    $http.post('/metrics/users', data).success(function(data, status, headers, config) {
        $scope.message = data;
        getUsers();
        console.log($scope.message.message);
    }).error(function(data, status, headers, config) { });
  }

  // удаление пользователя
  $scope.deleteUser = function(user) {
    $http.delete('/metrics/users/' + user).success(function(data, status, headers, config) {
        $scope.message = data;
        getUsers();
        console.log($scope.message.message);
    }).error(function(data, status, headers, config) { });
  }

  $scope.getMetrics = function(metrics) {
    month = metrics.date.getMonth() + 1;
    year  = metrics.date.getFullYear();
    $http.get('/metrics/get?users=' + $scope.selection + '&month=' + month + '&year=' + year + '&daysInMonth=' + metrics.days).success(function(data, status, headers, config) {
      $scope.gotmetrics = data;
    }).error(function(data, status, headers, config) { });
  }
  
});