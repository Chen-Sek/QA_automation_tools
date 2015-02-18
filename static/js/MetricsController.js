var app = angular.module('AutomationTools', []);

app.config(['$interpolateProvider', function($interpolateProvider) {
  $interpolateProvider.startSymbol('[[');
  $interpolateProvider.endSymbol(']]');
}]);

app.controller('MetricsController', function($scope, $http){

  $scope.selection = [];

  $('.mpopup').popup();

  $scope.addUserDisableClass = 'disabled';
  $scope.metricsDisableClass = 'enabled';
  
  // если имя пользователя указано, разрешаем его добавить
  $scope.checkUserName = function() {
    if($scope.newUser.name == '') $scope.addUserDisableClass = 'disabled';
    else $scope.addUserDisableClass = 'enabled';
  }

  // если количество рабочих дней указано, разрешаем расчет метрик
  $scope.checkWorkdays = function() {
    console.log($scope.metrics.days);
    if($scope.metrics.days == null) $scope.metricsDisableClass = 'disabled';
    else $scope.metricsDisableClass = 'enabled';
  }
  
  // сегодняшняя дата
  var today = new Date();

  // дата для datepicker
  $scope.metrics = { 'date': today, 'days': '' };
  // получение количества рабочих дней в месяце
  function getWorkdays(date) {
    $http.get('/metrics/workdays/' + date.getFullYear() + '/' + (date.getMonth() + 1)).success(function(data, status, headers, config) {
      $scope.metrics.days = data.workdays;
      console.log("got " + '/metrics/workdays/' + date.getFullYear() + '/' + (date.getMonth() + 1));
    }).error(function(data, status, headers, config) {});
  }
  getWorkdays(today);

  $scope.updateWorkdaysCount = function(date) {
    getWorkdays(date);
    getMetricsFromDB($scope.metrics);
  }

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

  //подсчет суммы по отделу
  function totalMetrics(metrics) {
    var total = {  'bugs_blocker_critical_major'    : 0,
                   'bugs_minor_trivial_improvements': 0,
                   'worktime'                       : 0,
                   'hours_required'                 : 0,
                   'days_missed'                    : 0,
                   'original_estimate'              : 0,
                   'time_spent'                     : 0,
                   'oe_ts'                          : 0,
                   'logging_quality'                : 0,
                   'time_internal'                  : 0,
                   'time_testing'                   : 0,
                   'issues_count'                   : 0,
                   'testing_velocity'               : 0 }

    for (var i = 0; i <  metrics.length; ++i) {
      total.bugs_blocker_critical_major     += (metrics[i].bugs_blocker + metrics[i].bugs_critical + metrics[i].bugs_major)
      total.bugs_minor_trivial_improvements += (metrics[i].bugs_minor + metrics[i].bugs_trivial + metrics[i].improvements)
      total.worktime                        +=  metrics[i].worktime                       
      total.hours_required                  +=  metrics[i].hours_required                 
      total.days_missed                     +=  metrics[i].days_missed                    
      total.original_estimate               +=  metrics[i].original_estimate              
      total.time_spent                      +=  metrics[i].time_spent                     
      total.oe_ts                           +=  metrics[i].oe_ts                          
      total.logging_quality                 +=  metrics[i].logging_quality                
      total.time_internal                   +=  metrics[i].time_internal                  
      total.time_testing                    +=  metrics[i].time_testing                   
      total.issues_count                    +=  metrics[i].issues_count                   
      total.testing_velocity                +=  metrics[i].testing_velocity               
    }
    return total;
  }

  // получение метрик из jira
  $scope.getMetrics = function(metrics) {
    $scope.metricsDisableClass = "loading";
    month = metrics.date.getMonth() + 1;
    year  = metrics.date.getFullYear();
    $http.get('/metrics/get?users=' + $scope.selection + '&month=' + month + '&year=' + year + '&daysInMonth=' + metrics.days).success(function(data, status, headers, config) {
      $scope.gotmetrics = data;
      $scope.totalmetrics = totalMetrics($scope.gotmetrics);
      console.log("metrics recieved.");
      $scope.metricsDisableClass = "enabled";
    }).error(function(data, status, headers, config) { });
  }

  // получение метрик из БД
  function getMetricsFromDB(metrics) {
    month = metrics.date.getMonth() + 1;
    year  = metrics.date.getFullYear();
    $http.get('/metrics/get?month=' + month + '&year=' + year + '&daysInMonth=' + metrics.days).success(function(data, status, headers, config) {
      $scope.gotmetrics = data;
      $scope.totalmetrics = totalMetrics($scope.gotmetrics);
    }).error(function(data, status, headers, config) { });
  }
  getMetricsFromDB($scope.metrics);
  
});