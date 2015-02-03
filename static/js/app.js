(function(){
  var app = angular.module('AutomationTools', []);

  app.config(['$interpolateProvider', function($interpolateProvider) {
    $interpolateProvider.startSymbol('[[');
    $interpolateProvider.endSymbol(']]');
  }]);

  app.controller('MainController', function($scope){
    $scope.show_weekly_builds = true;
    $scope.show_builds = function() {
      $scope.show_weekly_builds = true;
    }
    $scope.show_other = function() {
      $scope.show_weekly_builds = false;
    }
  });

  app.controller('AuthController', function($scope, $http){
    $scope.show_builds = false
    $scope.selected_build = false
    $scope.current_plan = ""
    //получаем параметры приложения
    $http.get('/settings').success(function(data, status, headers, config) {
        $scope.settings = data;
      }).error(function(data, status, headers, config) { });

    // получаем список добавленных планов
    $http.get('/plans').success(function(data, status, headers, config) {
        $scope.existingPlans = data;
      }).error(function(data, status, headers, config) { }); 

    $scope.bambooAuth = function(user) {
      $http.get('/auth').success(function(data, status, headers, config) {
        $scope.plans = data.plans.plan;
      }).error(function(data, status, headers, config) { }); 
    }
    
    $scope.bambooAddPlan = function(name, key) {
      var data = { name: name, 
                   key:  key }
      $http.post('/plans', data).success(function(data, status, headers, config) {
        $scope.result = data;
      }).error(function(data, status, headers, config) { }); 
    }

    $scope.bambooGetBuilds = function(key, name) {
      $scope.selected_build = false
      $http.get('/plans/' + key + '/builds').success(function(data, status, headers, config) {
        $scope.builds = data.results.result;
        $scope.current_plan = name;
      }).error(function(data, status, headers, config) { }); 
      $scope.show_builds = true;
    }
    
    // страница загрузки выбранной сборки
    $scope.selectBuild = function(build) {
      $scope.show_builds = false;
      $scope.selected_build = true;
      $scope.beginDate = build.prettyBuildStartedTime;
      $scope.endDate = build.prettyBuildCompletedTime;
      $scope.duration = build.buildDurationDescription;
      $scope.plan = build.planName;
      $scope.number = build.buildNumber;

      $scope.artifact = "test";
      artifacts = build.artifacts.artifact;
      for(i = 0; i < artifacts.length; ++i) {
        if(artifacts[i].name == "installer")
          $scope.artifact = artifacts[i];
      }
      //$http.post('/plans', data).success(function(data, status, headers, config) {
      //  $scope.result = data;
      //}).error(function(data, status, headers, config) { }); 
    }

  });

})();


