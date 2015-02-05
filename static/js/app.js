(function(){
  var app = angular.module('AutomationTools', []);

  app.config(['$interpolateProvider', function($interpolateProvider) {
    $interpolateProvider.startSymbol('[[');
    $interpolateProvider.endSymbol(']]');
  }]);

  app.controller('MainController', function($scope){
    $scope.menuBuildsActiveClass = 'active'
    $scope.show_weekly_builds = true;
    $scope.show_builds = function() {
      $scope.show_weekly_builds = true;
    }
    $scope.show_other = function() {
      $scope.show_weekly_builds = false;
    }
  });

  app.controller('AuthController', function($scope, $http, $interval){
    $scope.show_builds = false
    $scope.selected_build = false
    $scope.current_plan = ""

    //получаем параметры приложения
    $http.get('/settings').success(function(data, status, headers, config) {
        $scope.settings = data;
      }).error(function(data, status, headers, config) { });

    // получение списка добавленных планов
    function getAddedPlans() {
      $http.get('/plans').success(function(data, status, headers, config) {
          $scope.existingPlans = data;
          existingPlans = data;
        }).error(function(data, status, headers, config) { }); 
    }

    // получение планов с bamboo
    bambooAuth = function() {
      $http.get('/auth').success(function(data, status, headers, config) {
        $scope.bambooPlans = data.plans.plan;
      }).error(function(data, status, headers, config) { }); 
    }
    bambooAuth()
    
    // функция добавления плана в БД
    $scope.bambooAddPlan = function(name, key, filters, page) {
      var data = { name:    name, 
                   key:     key,
                   filters: filters ,
                   page:    page }
      $http.post('/plans', data).success(function(data, status, headers, config) {
        $scope.result = data;
      }).error(function(data, status, headers, config) { });
    }
    
    // выбор плана и получение сборок.
    // если план не настроен (не добавлен в БД с нужными параметрами),
    // то выбор сборок должен быть запрещен
    // нужно показывать кнопку настройки (добавления в БД)
    $scope.bambooGetBuilds = function(key, name) {
      // список добавленных планов
      
      $http.get('/plans').success(function(data, status, headers, config) {
        $scope.existingPlans = data;
        existingPlans = data;
        for(var i = 0; i < existingPlans.length; ++i) {
            $scope.buildsControlClass = 'disabled';
          if(key == existingPlans[i].bamboo_plan) {
            $scope.buildsControlClass = 'enabled';
          }
        }

      }).error(function(data, status, headers, config) { }); 

      // класс для отключения строк таблицы
      $scope.buildsControlClass = 'disabled';
      // пока данные не получены, список сборок не отображаем
      $scope.show_builds = false;
      // скрыаваем страницу выбранной сборки
      $scope.selected_build = false
      // отображаем заглушку
      $scope.show_placeholder = true
      // разные постфиксы для разных планов
      postfix = ""
      if(key.indexOf("AN3") > -1)
        postfix = '-JOB1'

      // запрашиваем список сборок с bamboo
      $http.get('/plans/' + key + postfix + '/builds').success(function(data, status, headers, config) {
        // список сборок
        $scope.builds = data.results.result;
        $scope.current_plan = name;
        // отображаем список
        $scope.show_builds = true;
        // скрываем подложку
        $scope.show_placeholder = false

      }).error(function(data, status, headers, config) { }); 
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
      $scope.total = 0;
      $scope.downloaded = 0;

      $scope.artifacts = [];
      a = build.artifacts.artifact;
      for(i = 0; i < a.length; ++i) {
        if(a[i].name.indexOf("installer") > -1 || a[i].name.indexOf("Installer") > -1)
          $scope.artifacts.push(a[i].link.href);
      }
      //$http.post('/plans', data).success(function(data, status, headers, config) {
      //  $scope.result = data;
      //}).error(function(data, status, headers, config) { }); 
    }
    
    //название кнопки
    $scope.downloadButtonName = "Выложить сборку"
    //управление доступностью контролов во время загрузки сборки
    $scope.controlClass = '';
    var downloadProgress;
    // загрузка сборки
    $scope.downloadBuild = function(link) {
      $scope.total = 0;
      $scope.downloaded = 0;
      var data = { "link": link}
      $http.post('/download', data).success(function(data, status, headers, config) {
        $scope.result = data;
        //запускаем обновление загруженного количества байт
        downloadProgress = $interval(getProgress, 1000);
      }).error(function(data, status, headers, config) { }); 
      $scope.downloadButtonName = "Сборка загружается"
      $scope.controlClass = 'disabled';
      $scope.showDownloadProgress = true;
    }

    // отмена загрузки
    $scope.cancelDownload = function() {
      $http.get('/download/cancel').success(function(data, status, headers, config) {
          // останавливаем обновление
          $interval.cancel(downloadProgress);
          $scope.downloadButtonName = "Выложить сборку"
          $scope.controlClass = 'enabled';
          $scope.showDownloadProgress = false;
      }).error(function(data, status, headers, config) { }); 
    }

    // получение прогресса загрузки
    function getProgress() {
      $http.get('/download/progress').success(function(data, status, headers, config) {
        $scope.total = Math.round(data.total / 1024 / 1024);
        $scope.downloaded = Math.round(data.downloaded / 1024 / 1024);

        // прогресс бар
        $('#dlProgress').progress({
          percent: Math.floor($scope.downloaded * 100 / $scope.total)
        });

        if($scope.downloaded == $scope.total && $scope.showDownloadProgress == true) {
          $scope.downloadButtonName = "Выложить сборку"
          $scope.controlClass = 'enabled';
          //$scope.showDownloadProgress = false;
        } else {
          //$scope.controlClass = 'disabled';
        }
      }).error(function(data, status, headers, config) { }); 
    }

  });

})();


