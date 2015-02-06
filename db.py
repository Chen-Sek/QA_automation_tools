from peewee import *
from time import gmtime, strftime
import os

# Путь к БДы
path = 'db\\'

# БД параметров
settings_db = SqliteDatabase(path + 'settings.db')

# основные параметры
parameters = [   { 'name': 'bamboo_token',     'value': ' '},
				 { 'name': 'jira_token',       'value': ' '},
				 { 'name': 'confluence_token', 'value': ' '},
				 { 'name': 'bamboo_url',       'value': 'https://build.itvgroup.ru/bamboo/rest/api/latest/'},   # url api build сервера
				 { 'name': 'jira_url',         'value': 'https://support.axxonsoft.com/jira/rest/api/latest/'},   # url api jira
				 { 'name': 'confluence_url',   'value': 'https://doc.axxonsoft.com/confluence/rest/api/latest/'}    # url api confluence
				 ]
#________________ схема данных ________________

# таблица основных параметров
class MainSettings(Model):
	name  = CharField(default = "")
	value = CharField(default = "")
	class Meta:
		database = settings_db

# таблица параметров раздела weekly builds
class WeeklyBuilds(Model):
	#owner      = ForeignKeyField(Monitor_type, related_name='monitors') # тип
	name                = CharField(default = "") # название сборки
	bamboo_plan         = CharField(default = "") # план build сервера (key)
	jira_filter_issues  = CharField(default = "") # фильтр jira Известные проблемы
	jira_filter_checked = CharField(default = "") # фильтр jira Проверено QA
	prev_date           = CharField(default = "2015-01-22")
	confluence_page     = CharField(default = "") # страница confluence
	class Meta:
		database = settings_db

#________________ инициализация базы данных ________________

# операции с БД параметров
class SettingsDB(object):
	def __init__(self):
		# создание БД и ее схемы, если ее нет
		try: # создание таблиц
			WeeklyBuilds.create_table()
			MainSettings.create_table()
			print("Settings database has been created")
		except:
			print("Settings database schema loaded")
		# инициализация основлных параметров
		for p in parameters:
			try:
				MainSettings.get(MainSettings.name == p['name'])
			except:
				parameter = MainSettings.create(name = p['name'], value = p['value'])
				parameter.save()

		# инициализация паарметров сборок
		#try:
		#	WeeklyBuilds.get(WeeklyBuilds.name == "Axxon Next v.3.6.3")
		#except:
		#	build = WeeklyBuilds.create(name = "Axxon Next v.3.6.3")
		#	build.save()

##________________ операции с БД ________________

	# редактирование основных параметров
	# создавать и удалять их нельзя
	def editMainSettings(self, name, value):
		if(name != None and value != None):
			parameter = MainSettings.get(MainSettings.name == name)
			parameter.value = value
			if(parameter.save()):
				print("Parameter " + name + " updated")
				return True
			else:
				return False
		else:
			return False

	def getMainSettings(self):
		settings = {}
		for s in MainSettings.select():
			settings[s.name] = s.value
		return settings

	# новый план
	def createBuild(self, name, plan, filter_issues, filter_checked, prev_date, page):
		if(name == None):
			_name = "New build"
		else:
			_name = name
		if(plan != None):
			WeeklyBuilds.create(name                = _name,
								bamboo_plan         = plan,
								jira_filter_issues  = filter_issues,
								jira_filter_checked = filter_checked,
								prev_date           = prev_date,
								confluence_page     = page)
			print("Build " + _name + " has been created")
			return True
		else:
			return False

	# обновление плана
	def updateBuild(self, plan = None, name = None, filter_issues = None, filter_checked = None, prev_date = None, page = None):
		if(plan != None):
			try:
				build = WeeklyBuilds.get(WeeklyBuilds.bamboo_plan == plan)
			except:
				return False
			if(name != None):
				build.name                = name
			if(filter_issues != None):
				build.jira_filter_issues  = filter_issues
			if(filter_checked != None):
				build.jira_filter_checked = filter_checked
			if(prev_date != None):
				build.prev_date           = prev_date
			if(page != None):
				build.confluence_page     = page
			if(build.save()):
				return True
			else:
				return False
		else:
			return False

	# удаление плана
	def removeBuild(self, plan):
		if(plan != None):
			try:
				build = WeeklyBuilds.get(WeeklyBuilds.bamboo_plan == plan)
				build.delete_instance()
				return True
			except:
				return False
		else:
			return False

	# получить список созданных планов
	def getBuilds(self):
		builds = []
		for b in WeeklyBuilds.select():
			build = {'name': b.name, 'bamboo_plan': b.bamboo_plan, 'jira_filter_issues': b.jira_filter_issues, 'jira_filter_checked': b.jira_filter_checked, 'prev_date': b.prev_date, 'confluence_page': b.confluence_page}
			builds.append(build)
		return builds

	# получить план по ключу
	def getBuild(self, key):
		build = {}
		try:
			b = WeeklyBuilds.get(WeeklyBuilds.bamboo_plan == key)
			build = {'name': b.name, 'bamboo_plan': b.bamboo_plan, 'jira_filter_issues': b.jira_filter_issues, 'jira_filter_checked': b.jira_filter_checked, 'prev_date': b.prev_date, 'confluence_page': b.confluence_page}
		except:
			pass
		return build