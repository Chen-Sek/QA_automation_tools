
(function () {
    'use strict';
     angular.module('AutomationTools', []).config(['$interpolateProvider', function($interpolateProvider) {
       $interpolateProvider.startSymbol('[[');
       $interpolateProvider.endSymbol(']]');
     }]);
})();