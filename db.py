from peewee import *
from time import gmtime, strftime
import os

# Путь к БДы
path = 'db\\'

# БД параметров
settings_db = SqliteDatabase(path + 'settings.db')
# БД метрик
metrics_db = SqliteDatabase(path + 'metrics.db')

# БД параметров____________________________________________________________________________________________________________________

# основные параметры
parameters = [   { 'name': 'bamboo_token',     'value': ' '},
				 { 'name': 'jira_token',       'value': ' '},
				 { 'name': 'confluence_token', 'value': ' '},
				 { 'name': 'bamboo_url',       'value': 'https://build.itvgroup.ru/bamboo/'},   # url api build сервера
				 { 'name': 'jira_url',         'value': 'https://support.axxonsoft.com/jira/'},   # url api jira
				 { 'name': 'confluence_url',   'value': 'https://doc.axxonsoft.com/confluence/'}    # url api confluence
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
	prev_date           = CharField(default = "2015-01-01")
	confluence_page     = CharField(default = "") # страница confluence
	class Meta:
		database = settings_db

# БД метрик_________________________________________________________________________________________________________________________
class mUser(Model):
	name = CharField(default = "")
	class Meta:
		database = metrics_db

class Metrics(Model):
	user             = ForeignKeyField(mUser, related_name='metrics')
	# месяц
	month            = IntegerField(default = "0")
	# год
	year             = IntegerField(default = "0")
	
	# кол-во багов типа blocker
	bugs_blocker     = IntegerField(default = "0")
	# кол-во багов типа critical
	bugs_critical    = IntegerField(default = "0")
	# кол-во багов типа major
	bugs_major       = IntegerField(default = "0")
	# кол-во багов типа minor
	bugs_minor       = IntegerField(default = "0")
	# кол-во багов типа trivial
	bugs_trivial     = IntegerField(default = "0")
	# кол-во improvements
	improvements     = IntegerField(default = "0")
	# кол-во project requirements
	requirements     = IntegerField(default = "0")
	# общее кол-во задач
	issues_count     = FloatField(default = "0")
	
	# запланированное время в Jira
	original_estimate= FloatField(default = "0")
	# затраченное время в Jira
	time_spent       = FloatField(default = "0")
	# время на внутренние задачи
	time_internal    = FloatField(default = "0")
	# общее рабочее время
	time_total       = FloatField(default = "0")
	# время на тестирование
	time_testing     = FloatField(default = "0")
	# требуемое время в часах
	hours_required   = FloatField(default = "0")
	# пропущено дней
	days_missed      = FloatField(default = "0")
	# качество логирования времени
	logging_quality  = FloatField(default = "0")
	# скорость тестирования
	testing_velocity = FloatField(default = "0")
	#
	oe_ts            = FloatField(default = "0")
	
	class Meta:
		database = metrics_db

# операции с БД метрик______________________________________
#________________ инициализация базы данных ________________

# операции с БД метрик
class MetricsDB(object):
	def __init__(self):
		# создание БД и ее схемы, если ее нет
		try: # создание таблиц
			mUser.create_table()
			Metrics.create_table()
			print("Metrics database has been created")
		except:
			print("Metrics database schema loaded")

	# операции с пользователями
	def addmUser(self, username):
		if(not mUser.select().where(mUser.name == username).exists()):
			try:
				mUser.create(name = username)
				return True
			except:
				return False
		else:
			return False

	def removemUser(self, username):
		try:
			user = mUser.get(mUser.name == username)
			user.delete_instance()
			return True
		except:
			return False

	def getmUsers(self):
		users = []
		for u in mUser.select():
			user = {'name': u.name, 'id': u.id }
			users.append(user)
		return users

	def getmUser(self, username):
		try:
			user = mUser.get(mUser.name == username)
			return {'name': user.name, 'id': user.id }
		except:
			return False

	# операции с метриками
	def addMetrics(self, values):
		try:
			user           = mUser.get(mUser.id == values['user_id'])
		except:
			print("error get user")
			return False
		try:
			month            = values['month']
		except:
			month            = 0
		try:
			year             = values['year']
		except:
			year             = 0
		
		try:
			bugs_blocker     = values['bugs_blocker']
		except:
			bugs_blocker     = 0
		try:
			bugs_critical    = values['bugs_critical']
		except:
			bugs_critical    = 0
		try:
			bugs_major       = values['bugs_major']
		except:
			bugs_major       = 0
		try:
			bugs_minor       = values['bugs_minor']
		except:
			bugs_minor       = 0
		try:
			bugs_trivial     = values['bugs_trivial']
		except:
			bugs_trivial     = 0
		try:
			improvements     = values['improvements']
		except:
			improvements     = 0
		try:
			requirements     = values['requirements']
		except:
			requirements     = 0
		try:
			issues_count     = values['issues_count']
		except:
			issues_count     = 0
		try:
			original_estimate= values['original_estimate']
		except:
			original_estimate= 0
		try:
			time_spent       = values['time_spent']
		except:
			time_spent       = 0
		try:
			time_internal    = values['time_internal']
		except:
			time_internal    = 0
		try:
			time_total       = values['time_total']
		except:
			time_total       = 0
		try:
			time_testing     = values['time_testing']
		except:
			time_testing     = 0
		try:
			hours_required   = values['hours_required']
		except:
			hours_required   = 0
		try:
			days_missed      = values['days_missed']
		except:
			days_missed      = 0
		try:
			logging_quality  = values['logging_quality']
		except:
			logging_quality  = 0
		try:
			testing_velocity = values['testing_velocity']
		except:
			testing_velocity = 0
		try:
			oe_ts            = values['oe_ts']
		except:
			oe_ts            = 0

		m = Metrics.select().where( (Metrics.user ==  values['user_id']) & (Metrics.month ==  month) & (Metrics.year ==  year) )
		if(m.exists()):
			# print("record exists. Updating...")
			met = Metrics.update(
								bugs_blocker     = bugs_blocker,
								bugs_critical    = bugs_critical,
								bugs_major       = bugs_major,
								bugs_minor       = bugs_minor,
								bugs_trivial     = bugs_trivial,
								improvements     = improvements,
								requirements     = requirements,
								issues_count     = issues_count,
								original_estimate= original_estimate,
								time_spent       = time_spent,
								time_internal    = time_internal,
								time_total       = time_total,
								time_testing     = time_testing,
								hours_required   = hours_required,
								days_missed      = days_missed,
								logging_quality  = logging_quality,
								testing_velocity = testing_velocity,
								oe_ts            = oe_ts).where( (Metrics.user ==  values['user_id']) & (Metrics.month ==  month) & (Metrics.year ==  year) )
			met.execute()
		else:
			Metrics.create( user             = user,            
							month            = month,
							year             = year,
							bugs_blocker     = bugs_blocker,
							bugs_critical    = bugs_critical,
							bugs_major       = bugs_major,
							bugs_minor       = bugs_minor,
							bugs_trivial     = bugs_trivial,
							improvements     = improvements,
							requirements     = requirements,
							issues_count     = issues_count,
							original_estimate= original_estimate,
							time_spent       = time_spent,
							time_internal    = time_internal,
							time_total       = time_total,
							time_testing     = time_testing,
							hours_required   = hours_required,
							days_missed      = days_missed,
							logging_quality  = logging_quality,
							testing_velocity = testing_velocity,
							oe_ts            = oe_ts)
		return True

	def getMetrics(self, month, year):
		metrics = []
		for m in Metrics.select().where( (Metrics.month ==  month) & (Metrics.year ==  year) ):
			#print(m.id)
			metric = {  'id'               : m.id, 
						'user_id'          : m.user.name,          
						'month'            : m.month,
						'year'             : m.year,
						'bugs_blocker'     : m.bugs_blocker,
						'bugs_critical'    : m.bugs_critical,
						'bugs_major'       : m.bugs_major,
						'bugs_minor'       : m.bugs_minor,
						'bugs_trivial'     : m.bugs_trivial,
						'improvements'     : m.improvements,
						'requirements'     : m.requirements,
						'issues_count'     : m.issues_count,
						'original_estimate': m.original_estimate,
						'time_spent'       : m.time_spent,
						'time_internal'    : m.time_internal,
						'time_total'       : m.time_total,
						'time_testing'     : m.time_testing,
						'hours_required'   : m.hours_required,
						'days_missed'      : m.days_missed,
						'logging_quality'  : m.logging_quality,
						'testing_velocity' : m.testing_velocity,
						'oe_ts'            : m.oe_ts }
			metrics.append(metric)
		return metrics



# операции с БД параметров__________________________________
#________________ инициализация базы данных ________________
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
	def createBuild(self, plan, name, filter_issues, filter_checked, prev_date, page):
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
				print("DB error")
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
				print("Save error")
				return False
		else:
			print("Plan = None")
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