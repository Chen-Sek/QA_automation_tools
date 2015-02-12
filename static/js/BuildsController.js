(function () {
    'use strict';
var app = angular.module('AutomationTools', []);

app.controller('BuildsController', function($scope, $http, $interval){
  $scope.show_builds = false;
  $scope.show_plans = false;
  $scope.selected_build = false;
  $scope.current_plan = ""

  //получаем параметры приложения
  $http.get('/settings').success(function(data, status, headers, config) {
      $scope.settings = data;
    }).error(function(data, status, headers, config) { });

  // получение списка добавленных планов
  function getAddedPlans(currentKey) {
    $http.get('/plans').success(function(data, status, headers, config) {
        // для отладки
        $scope.existingPlans = data;
        // если текущий план в добавленных, делаем таблицу доступной
        existingPlans = data;
        for(var i = 0; i < existingPlans.length; ++i) {
          if(currentKey == existingPlans[i].bamboo_plan) {
            $scope.buildsControlClass = 'enabled';
            $scope.currentExistingPlan = existingPlans[i];
          }
        }
      }).error(function(data, status, headers, config) { }); 
  }

  // получение планов с bamboo
  bambooAuth = function() {
    $http.get('/auth').success(function(data, status, headers, config) {
      $scope.bambooPlans = data.plans.plan;
      $scope.show_plans = true;
    }).error(function(data, status, headers, config) { }); 
  }
  bambooAuth()
  
  // функция добавления плана в БД
  // plan - данные формы,
  // key - ключ (id) плана
  $scope.bambooAddPlan = function(plan, key) {
    // показываем сообщения
    $scope.showGreenMessage = true;

    var data = { bamboo_plan:         key,
                 jira_filter_issues:  plan.jira_filter_issues,
                 jira_filter_checked: plan.jira_filter_checked,
                 prev_date:           plan.prev_date,
                 confluence_page:     plan.confluence_page };

    $http.post('/plans', data).success(function(data, status, headers, config) {
      $scope.result = data;
      // $scope.result.message - сообщение для пользателя
      // $scope.result.key - ключ добавленного плана

      // обновляем список добавленных планов
      getAddedPlans($scope.result.key);
    }).error(function(data, status, headers, config) { });
  }
  
  // выбор плана и получение сборок.
  // если план не настроен (не добавлен в БД с нужными параметрами),
  // то выбор сборок должен быть запрещен
  // нужно показывать кнопку настройки (добавления в БД)
  $scope.bambooGetBuilds = function(key, name) {
    // скрываем сообщения
    $scope.showGreenMessage = false;
    // скрываем форму
    $scope.showForm = false;
    // ключ плана
    $scope.currentKey = key;
    // пока данные не получены, список сборок не отображаем
    $scope.show_builds = false;
    // скрыаваем страницу выбранной сборки
    $scope.selected_build = false
    // отображаем заглушку
    $scope.show_placeholder = true
    // класс для отключения строк таблицы
    $scope.buildsControlClass = 'disabled';
    
    // запрашиваем список добавленных планов
    $http.get('/plans').success(function(data, status, headers, config) {
      existingPlans = data;
      $scope.existingPlans = data; // для отладки
      // если текущий план не в добавленных, блокируем таблицу
      for(var i = 0; i < existingPlans.length; ++i) {
        if(key == existingPlans[i].bamboo_plan) {
          $scope.buildsControlClass = 'enabled';
          $scope.currentExistingPlan = existingPlans[i];
        }
      }
    }).error(function(data, status, headers, config) { }); 

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

  var _currentState;

  function getState() {
    // проверка, запущена ли другая публикация
    $http.get('/download/state').success(function(data, status, headers, config) {
      $scope.currentState = data;
      if($scope.currentState.result == "busy") {
        $scope.controlClass = 'disabled';
        console.log($scope.currentState.message)
      }
      else {
        $interval.cancel(_currentState);
        $scope.controlClass = 'enabled';
        console.log($scope.currentState.message);
      }
    }).error(function(data, status, headers, config) { });
  }

  // страница загрузки выбранной сборки
  $scope.selectBuild = function(build) {
    _currentState = $interval(getState, 1000);

    $scope.show_builds = false;
    $scope.showDownloadProgress = false;
    $scope.selected_build = true;
    $scope.beginDate = build.prettyBuildStartedTime;
    $scope.endDate = build.prettyBuildCompletedTime;
    $scope.duration = build.buildDurationDescription;
    $scope.link = build.link.href.substring(0, 33) + 'browse/' +  build.buildResultKey;
    $scope.timeAgo = build.buildRelativeTime;
    $scope.plan = build.planName;
    $scope.number = build.buildNumber;
    $scope.total = 0;
    $scope.downloaded = 0;
    // отключаем кнопки изменения jira и confluence, пока сборка не загрузится
    $scope.controlPagesButtonClass = 'displaynone'
    $scope.controlFiltersButtonClass = 'displaynone'

    //скрываем сообщения
    $scope.showFiltersMessage = false;
    $scope.showPageMessage = false;

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
  var downloadCurrentState;

  // загрузка сборки
  $scope.downloadBuild = function(link) {
    
    $http.get('/download/state').success(function(data, status, headers, config) {
      $scope.currentState = data;
      if($scope.currentState.result == "busy") {
        $scope.controlClass = 'disabled';
        console.log("publication is in progress!");
        //downloadCurrentState = $interval(getState, 1000);
      }
      else {
        console.log("Ready to go!");
        $http.get('/download/cancel').success(function(data, status, headers, config) {
  
        }).error(function(data, status, headers, config) { });
  
        // сброс счетчиков прогресс бара
        $http.get('/download/clear').success(function(data, status, headers, config) {
  
        }).error(function(data, status, headers, config) { }); 
  
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
    }).error(function(data, status, headers, config) { });
    

  }

  $scope.backToBuildsList = function() {
    $scope.show_builds = true;
    $scope.selected_build = false;
    $interval.cancel(downloadCurrentState);
  }

  // отмена загрузки
  $scope.cancelDownload = function() {
    $http.get('/download/cancel').success(function(data, status, headers, config) {
        // останавливаем обновление
        $interval.cancel(downloadProgress);
        $scope.downloadButtonName = "Выложить сборку"
        $scope.controlClass = 'enabled';
        $scope.controlPagesButtonClass = 'displaynone'
        $scope.controlFiltersButtonClass = 'displaynone'
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
      // если загрузка завершена
      if($scope.downloaded == $scope.total && $scope.showDownloadProgress == true) {
        //$interval.cancel(downloadCurrentState);
        $scope.downloadButtonName = "Выложить сборку"
        $scope.controlClass = 'enabled';
        $scope.controlPagesButtonClass = ''
        $scope.controlFiltersButtonClass = ''
        $interval.cancel(downloadProgress);
        // получение имени загруженного файла
        $http.get('/download/filename').success(function(data, status, headers, config) {
          $scope.filename = data;
          $scope.updateFilters($scope.currentExistingPlan.bamboo_plan)
          $scope.updatePages($scope.currentExistingPlan.bamboo_plan, $scope.filename)
          // сброс счетчиков прогресс бара
          $http.get('/download/clear').success(function(data, status, headers, config) {}).error(function(data, status, headers, config) { }); 
        }).error(function(data, status, headers, config) { }); 
      } else {
        //$scope.controlClass = 'disabled';
      }
    }).error(function(data, status, headers, config) { }); 
  }

  // обновление фильтров
  $scope.updateFilters = function(key) {
    //скрываем сообщения
    $scope.showFiltersMessage = false;
    // отключаем кнопку
    $scope.controlFiltersButtonClass = 'displaynone';
    $http.get('/plans/' + key + '/updatefilters').success(function(data, status, headers, config) {
      $scope.controlFiltersButtonClass = '';
      // отображаем сообщения
      $scope.showFiltersMessage = true;
      $scope.result = data;
    }).error(function(data, status, headers, config) { }); 
  }

  // обновление страниц
  $scope.updatePages = function(key, filename) {
    //скрываем сообщения
    $scope.showPageMessage = false;
    // отключаем кнопку
    var data = { filename: filename}
    $scope.controlPagesButtonClass = 'displaynone';
    $http.post('/plans/' + key + '/updatepages', data).success(function(data, status, headers, config) {
      $scope.controlPagesButtonClass = '';
      // отображаем сообщения
      $scope.showPageMessage = true;
      $scope.result = data;
    }).error(function(data, status, headers, config) { }); 
  }

});
})();

