(function(){
  var app = angular.module('AutomationTools', []);

  app.config(['$interpolateProvider', function($interpolateProvider) {
    $interpolateProvider.startSymbol('[[');
    $interpolateProvider.endSymbol(']]');
  }]);

  app.controller('MainController', function($scope){
    $scope.hello = "Hello,  fdsa world!";
    $scope.show_weekly_builds = true;
    $scope.show_builds = function() {
      $scope.show_weekly_builds = true;
    }
    $scope.show_other = function() {
      $scope.show_weekly_builds = false;
    }
  });
})();


