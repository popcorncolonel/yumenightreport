import endpoints
import jinja2
import os
import webapp2

from google.appengine.ext import ndb
from datetime import datetime, date


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True
)


def get_working_days_left_in_year(date_obj):
    ''' date_obj must be a `date` object. Returns the number of days left in the year of date_obj '''
    end_year = date(date_obj.year, month=12, day=31)
    days_until_year_end = (end_year - date_obj).days
    # exclude sundays & mondays
    working_days_until_year_end = max(0, int((6./7.) * days_until_year_end) - 4)
    return working_days_until_year_end


class GlobalStats(ndb.Model):
    '''
    Global information needed for all reports (like yearly dreamcount)
    '''
    customers_this_year = ndb.IntegerProperty()
    dreams_this_year = ndb.IntegerProperty()
    yearly_dream_goal = ndb.IntegerProperty()  # how many dreams would we like today?
    year_goal = ndb.StringProperty(default="")
    month_goal = ndb.StringProperty(default="")

    def daily_dream_goal(self, working_days_left_in_year=None, datetime_obj=None):
        dreams_remaining = max(0, self.yearly_dream_goal - self.dreams_this_year)
        if working_days_left_in_year is None:
            if datetime_obj is None:
                datetime_obj = datetime.now()
            working_days_left_in_year = get_working_days_left_in_year(datetime_obj.date())
        if working_days_left_in_year == 0:
            return 0.
        return dreams_remaining / working_days_left_in_year


def initialize_global_stats():
    global_stats = GlobalStats(
        id="global_stats",
        customers_this_year=26108,#-182,
        dreams_this_year=25484,#-135,
        yearly_dream_goal=40000,
        year_goal="Say less",
        month_goal="",
    )
    global_stats.put()
    return global_stats


def get_global_stats():
    global_stats_key = ndb.Key(GlobalStats, "global_stats")
    global_stats = global_stats_key.get()
    if global_stats is None:
        return GlobalStats()
    return global_stats


class Report(ndb.Model):
    '''
    Information for the daily report
    '''
    """ Global stats snapshot """
    customers_this_year = ndb.IntegerProperty()
    dreams_this_year = ndb.IntegerProperty()
    yearly_dream_goal = ndb.IntegerProperty()
    year_goal = ndb.StringProperty()
    month_goal = ndb.StringProperty()
    daily_dream_goal = ndb.IntegerProperty()

    date = ndb.DateTimeProperty()
    lunch_customers_today = ndb.IntegerProperty()
    dinner_customers_today = ndb.IntegerProperty()
    customers_today = ndb.IntegerProperty()
    lunch_dreams = ndb.IntegerProperty()
    dinner_dreams = ndb.IntegerProperty()
    dreams = ndb.IntegerProperty()
    lunch_dreamers = ndb.IntegerProperty()
    dinner_dreamers = ndb.IntegerProperty()
    dreamers = ndb.IntegerProperty()
       
    working_members = ndb.StringProperty()
    supporting_members = ndb.StringProperty()
    visiting_members = ndb.StringProperty()
    end_time = ndb.TimeProperty()
    total_bowls = ndb.IntegerProperty()
    total_cups = ndb.IntegerProperty()
    chopsticks_missing = ndb.IntegerProperty()
    money_off_by = ndb.IntegerProperty()
    positive_cycle = ndb.IntegerProperty()
    achievement_rate = ndb.FloatProperty()

    misc_notes = ndb.StringProperty()

    def update(self, old_report):
        '''
        StringProperties are not checked for None because they can be "" which we don't want
        '''
        if old_report.customers_this_year is not None: self.customers_this_year = old_report.customers_this_year
        if old_report.dreams_this_year is not None: self.dreams_this_year = old_report.dreams_this_year
        if old_report.yearly_dream_goal is not None: self.yearly_dream_goal = old_report.yearly_dream_goal
        if old_report.year_goal: self.year_goal = old_report.year_goal
        if old_report.month_goal: self.month_goal = old_report.month_goal
        if old_report.daily_dream_goal is not None: self.daily_dream_goal = old_report.daily_dream_goal
        if old_report.date is not None: self.date = old_report.date
        if old_report.customers_today is not None: self.customers_today = old_report.customers_today
        if old_report.lunch_customers_today is not None: self.lunch_customers_today = old_report.lunch_customers_today
        if old_report.dinner_customers_today is not None: self.dinner_customers_today = old_report.dinner_customers_today
        if old_report.dreams is not None: self.dreams = old_report.dreams
        if old_report.lunch_dreams is not None: self.lunch_dreams = old_report.lunch_dreams
        if old_report.dinner_dreams is not None: self.dinner_dreams = old_report.dinner_dreams
        if old_report.dreamers is not None: self.dreamers = old_report.dreamers
        if old_report.lunch_dreamers is not None: self.lunch_dreamers = old_report.lunch_dreamers
        if old_report.dinner_dreamers is not None: self.dinner_dreamers = old_report.dinner_dreamers
        if old_report.working_members: self.working_members = old_report.working_members
        if old_report.supporting_members: self.supporting_members = old_report.supporting_members
        if old_report.visiting_members: self.visiting_members = old_report.visiting_members
        if old_report.end_time is not None: self.end_time = old_report.end_time
        if old_report.total_bowls is not None: self.total_bowls = old_report.total_bowls
        if old_report.total_cups is not None: self.total_cups = old_report.total_cups
        if old_report.chopsticks_missing is not None: self.chopsticks_missing = old_report.chopsticks_missing
        if old_report.money_off_by is not None: self.money_off_by = old_report.money_off_by
        if old_report.positive_cycle is not None: self.positive_cycle = old_report.positive_cycle
        if old_report.achievement_rate is not None: self.achievement_rate = old_report.achievement_rate
        if old_report.misc_notes: self.misc_notes = old_report.misc_notes

    @property
    def date_string(self):
        ''' 2017-06-13 '''
        if self.date:
            return self.date.strftime('%Y-%m-%d')
        else:
            return None

    @property
    def readable_date_string(self):
        ''' Tuesday June 13, 2017 '''
        if self.date:
            return self.date.strftime('%A %B %d, %Y')
        else:
            return None


class ViewAllReportsHandler(webapp2.RequestHandler):
    '''
    Handler to view a list of all the existing daily reports
    '''
    def get(self):
        template_values = {}
        all_reports = [x for x in Report.query().iter()]
        sorted_reports = sorted(all_reports, key=lambda x: x.date, reverse=True)
        template_values['reports'] = sorted_reports

        template = JINJA_ENVIRONMENT.get_template('reports.html')
        self.response.write(template.render(template_values))


class ViewReportHandler(webapp2.RequestHandler):
    '''
    Handler to view details about a single report
    '''
    def get(self, date_string):
        '''
        Get corresponding report from date_string, if it exists. if not, 404
        We should allow editing of a report, which takes you to CreateReportHandler with all the info already pre-filled in
        '''
        template_values = {}
        report_key = ndb.Key(Report, date_string)
        current_report = report_key.get()
        if current_report is None:
            raise endpoints.NotFoundException("No report found for {}".format(date_string))
        report_dict = create_report_dict_from_report_obj(current_report)
        today_datetime = datetime.now()
        global_stats = get_global_stats()
        template_values['global_stats'] = global_stats
        template_values['report'] = report_dict
        template_values['today_date_string'] = today_datetime.strftime('%Y-%m-%d')
        template_values['hidetitleimg'] = True
        template = JINJA_ENVIRONMENT.get_template('report.html')
        self.response.write(template.render(template_values))


'''
Helper functions for `get_report_from_request`
'''
def get_integer_input(request, key, default=None):
    val = request.get(key, default)
    if val is not None and val != '':
        val = val.replace('$', '')
        int_val = int(val)
    else:
        int_val = None
    return int_val


def get_time_obj(end_time):
    if end_time:
        if ':' in end_time:
            end_time_obj = datetime.strptime(end_time, '%H:%M').time()  # deal w/ am/pm?
        else:
            end_time_obj = datetime.strptime(end_time, '%H%M').time()  # deal w/ am/pm?
    else:
        end_time_obj = None
    return end_time_obj


def get_date_obj(date):
    if date:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
    else:
        date_obj = None
    return date_obj


def get_old_report(date):
    if date != '':
        old_report_key = ndb.Key(Report, date)
        old_report = old_report_key.get()
    else:
        old_report = None
    return old_report


def get_global_stats_vars(
    current_global_stats,
    old_report, # The report from the previous date
    overwriting_report, # The report we're overwriting
    date_obj,
    dreams,
    customers_today,
):
    '''
    Gets the current global stats variables from global_stats if `old_report` is None,
    but gets the variables from the snapshot in `old_report` otherwise. 

    `date_obj` is the date of the report that is being submitted.
    '''
    if old_report is None:
        month_goal = current_global_stats.month_goal
        year_goal = current_global_stats.year_goal
        yearly_dream_goal = current_global_stats.yearly_dream_goal
        dreams_this_year = current_global_stats.dreams_this_year
        customers_this_year = current_global_stats.customers_this_year
        if dreams is not None:
            dreams_this_year += dreams
        if customers_today is not None:
            customers_this_year += customers_today
        if date_obj is not None:
            daily_dream_goal = current_global_stats.daily_dream_goal(get_working_days_left_in_year(date_obj.date()))
        else:
            daily_dream_goal = current_global_stats.daily_dream_goal()
    else:
        month_goal = old_report.month_goal
        year_goal = old_report.year_goal
        yearly_dream_goal = old_report.yearly_dream_goal
        dreams_this_year = old_report.dreams_this_year
        customers_this_year = old_report.customers_this_year
        if dreams is not None:
            dreams_this_year += dreams - old_report.dreams
        if customers_today is not None:
            customers_this_year += customers_today - old_report.customers_today
        daily_dream_goal = old_report.daily_dream_goal
    if overwriting_report is not None and overwriting_report != old_report:
        dreams_this_year -= overwriting_report.dreams
        customers_this_year -= overwriting_report.customers_today
    return month_goal, year_goal, yearly_dream_goal, dreams_this_year, customers_this_year, daily_dream_goal


def get_achievement_rate(dreams, daily_dream_goal):
    if dreams is None:
        achievement_rate = None
    else:
        if daily_dream_goal == 0:
            return 100.
        achievement_rate = (dreams / float(daily_dream_goal)) * 100
    return achievement_rate


def get_totals(
    lunch_customers_today,
    dinner_customers_today,
    lunch_dreams,
    dinner_dreams,
    lunch_dreamers,
    dinner_dreamers,
    ):
    if lunch_customers_today is not None and dinner_customers_today is not None:
        customers_today = lunch_customers_today + dinner_customers_today
    else:
        customers_today = None
    if lunch_dreams is not None and dinner_dreams is not None:
        dreams = lunch_dreams + dinner_dreams
    else:
        dreams = None
    if lunch_dreamers is not None and dinner_dreamers is not None:
        dreamers = lunch_dreamers + dinner_dreamers
    else:
        dreamers = None
    return customers_today, dreams, dreamers
def get_report_from_request(request, update_global_stats, prev_date=None):
    '''
    Naming convention: 
    * when reporting numbers/count of things don't do num_* or count_* just say the thing
    *    if something's in the report, use that name i.e. "total bowls" -> "total_bowls"
    * always spell out the full word i.e. "customers" over "cust"
    * separate all words with underscores
    * variable name and key name need to be the same
    '''
    date = request.get('date', '')
    lunch_customers_today = get_integer_input(request, 'lunch_customers_today')
    dinner_customers_today = get_integer_input(request, 'dinner_customers_today')
    lunch_dreams = get_integer_input(request, 'lunch_dreams')
    dinner_dreams = get_integer_input(request, 'dinner_dreams')
    lunch_dreamers = get_integer_input(request, 'lunch_dreamers')
    dinner_dreamers = get_integer_input(request, 'dinner_dreamers')
    working_members = request.get('working_members', '')
    supporting_members = request.get('supporting_members', '')
    visiting_members = request.get('visiting_members', '')
    end_time = request.get('end_time', '')
    total_bowls = get_integer_input(request, 'total_bowls')
    total_cups = get_integer_input(request, 'total_cups')
    chopsticks_missing = get_integer_input(request,'chopsticks_missing')
    money_off_by = get_integer_input(request, 'money_off_by')
    positive_cycle = get_integer_input(request, 'positive_cycle')

    customers_today, dreams, dreamers = get_totals(
        lunch_customers_today,
        dinner_customers_today,
        lunch_dreams,
        dinner_dreams,
        lunch_dreamers,
        dinner_dreamers,
    )
    misc_notes = request.get('misc_notes', '')

    end_time_obj = get_time_obj(end_time)
    date_obj = get_date_obj(date)

    overwriting_report = get_old_report(date)  # overwriting_report is the report we're overwriting by saving this report
    if prev_date:
        old_report = get_old_report(prev_date) # old_report is the report we're modifying
    else:
        old_report = None
    current_global_stats = get_global_stats()
    (month_goal,
     year_goal,
     yearly_dream_goal,
     dreams_this_year,
     customers_this_year,
     daily_dream_goal) = get_global_stats_vars(
        current_global_stats,
        old_report,
        overwriting_report,
        date_obj,
        dreams,
        customers_today,
    )
    achievement_rate = get_achievement_rate(dreams, daily_dream_goal)

    if update_global_stats:
        if old_report is not None:
            current_global_stats.customers_this_year -= old_report.customers_today
            current_global_stats.dreams_this_year -= old_report.dreams
        if overwriting_report is not None:
            if old_report is None or old_report.date_string != overwriting_report.date_string:
                current_global_stats.customers_this_year -= overwriting_report.customers_today
                current_global_stats.dreams_this_year -= overwriting_report.dreams
        current_global_stats.customers_this_year += customers_today
        current_global_stats.dreams_this_year += dreams
        current_global_stats.put()

    return Report(
        id=date, 
        date=date_obj, 
        lunch_customers_today=lunch_customers_today,
        dinner_customers_today=dinner_customers_today,
        customers_today=customers_today,
        lunch_dreams=lunch_dreams,
        dinner_dreams=dinner_dreams,
        dreams=dreams,
        lunch_dreamers=lunch_dreamers,
        dinner_dreamers=dinner_dreamers,
        dreamers=dreamers,
        working_members=working_members,
        supporting_members=supporting_members,
        visiting_members=visiting_members,
        end_time=end_time_obj,
        total_bowls=total_bowls,
        total_cups=total_cups,
        chopsticks_missing=chopsticks_missing,
        money_off_by=money_off_by,
        positive_cycle=positive_cycle,
        achievement_rate=achievement_rate,
        misc_notes=misc_notes,
        # global_stats snapshot:
        month_goal=month_goal,
        year_goal=year_goal,
        yearly_dream_goal=yearly_dream_goal,
        dreams_this_year=dreams_this_year,
        customers_this_year=customers_this_year,
        daily_dream_goal=daily_dream_goal,
    )


def create_report_dict_from_report_obj(current_report, preview=False):
    report_dict = {
        'daily_dream_goal': current_report.daily_dream_goal if current_report.daily_dream_goal is not None else '',
        'yearly_dream_goal': current_report.yearly_dream_goal if current_report.yearly_dream_goal is not None else '',
        'month_goal': current_report.month_goal if current_report.month_goal is not None else '',
        'year_goal': current_report.year_goal if current_report.year_goal is not None else '',
        'customers_this_year': current_report.customers_this_year if current_report.customers_this_year is not None else '',
        'dreams_this_year': current_report.dreams_this_year if current_report.dreams_this_year is not None else '',

        'datetime_obj': current_report.date,
        'date': current_report.date.strftime('%Y-%m-%d') if current_report.date is not None else '',
        'date_string': current_report.date.strftime('%Y-%m-%d') if current_report.date is not None else '',
        'readable_date_string': current_report.readable_date_string if current_report.readable_date_string is not None else '',
        'lunch_customers_today': current_report.lunch_customers_today if current_report.lunch_customers_today is not None else '',
        'dinner_customers_today': current_report.dinner_customers_today if current_report.dinner_customers_today is not None else '',
        'customers_today': current_report.customers_today if current_report.customers_today is not None else '',
        'lunch_dreams': current_report.lunch_dreams if current_report.lunch_dreams is not None else '',
        'dinner_dreams': current_report.dinner_dreams if current_report.dinner_dreams is not None else '',
        'dreams': current_report.dreams if current_report.dreams is not None else '',
        'lunch_dreamers': current_report.lunch_dreamers if current_report.lunch_dreamers is not None else '',
        'dinner_dreamers': current_report.dinner_dreamers if current_report.dinner_dreamers is not None else '',
        'dreamers': current_report.dreamers if current_report.dreamers is not None else '',
        'achievement_rate': '{:.2f}%'.format(current_report.achievement_rate) if current_report.achievement_rate is not None else '', 
        'working_members': current_report.working_members if current_report.working_members is not None else '',
        'supporting_members': current_report.supporting_members if current_report.supporting_members is not None else '',
        'visiting_members': current_report.visiting_members if current_report.visiting_members is not None else '',
        'end_time': current_report.end_time.strftime('%H:%M') if current_report.end_time is not None else '',
        'positive_cycle': current_report.positive_cycle if current_report.positive_cycle is not None else '',
        'total_bowls': current_report.total_bowls if current_report.total_bowls is not None else '',
        'total_cups': current_report.total_cups if current_report.total_cups is not None else '',
        'chopsticks_missing': current_report.chopsticks_missing if current_report.chopsticks_missing is not None else '',
        'money_off_by': current_report.money_off_by if current_report.money_off_by is not None else '',
        'misc_notes': current_report.misc_notes if current_report.misc_notes is not None else '',
    }
    return report_dict


class CreateReportHandler(webapp2.RequestHandler):
    '''
    Handler to create a new report.
        GET this endpoint to get a create report form
        POST here to save a new one do the db
    '''
    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('createreport.html')
        date_string = self.request.get('date', '')
        current_report_key = ndb.Key(Report, date_string)
        request_report = get_report_from_request(self.request, update_global_stats=False)
        if date_string:
            past_report = current_report_key.get()
            if past_report is not None:
                past_report.update(request_report)
                current_report = past_report
            else:
                current_report = request_report
        else:
            current_report = request_report
        assert current_report is not None
        report_dict = create_report_dict_from_report_obj(current_report)
        template_values['report'] = report_dict
        template_values['global_stats'] = get_global_stats()
        template_values['hidetitleimg'] = True
        self.response.write(template.render(template_values))

    def post(self):
        # get stuff from POST request
        # create a new Report object and save it to ndb
        old_date_string = self.request.get('old_date_string', None)
        new_report = get_report_from_request(self.request, update_global_stats=True, prev_date=old_date_string)
        new_report.put()
        if old_date_string:
            if old_date_string != new_report.date_string:
                delete_report(old_date_string)
        report_page = '/report/' + new_report.date.strftime('%Y-%m-%d')
        self.redirect(report_page)


class PreviewReportHandler(webapp2.RequestHandler):
    '''
    Handler to preview a report.
        GET this endpoint to get a create report form
        POST here to save a new one do the db
    '''
    def get(self):
        template_values = {}
        # create Report object based on self.request (using the same logic as ViewReportHandler)
        old_date_string = self.request.get('old_date_string', None)
        current_report = get_report_from_request(self.request, update_global_stats=False, prev_date=old_date_string)
        report_dict = create_report_dict_from_report_obj(current_report, preview=True)
        global_stats = get_global_stats()
        template_values['global_stats'] = global_stats
        template_values['report'] = report_dict
        template_values['preview'] = True
        template_values['hidetitleimg'] = True
        template_values['old_date_string'] = old_date_string
        template = JINJA_ENVIRONMENT.get_template('report.html')
        self.response.write(template.render(template_values))


class EditGoalHandler(webapp2.RequestHandler):
    '''
    Handler to edit the goals.
        GET this endpoint to get a edit goal form, where you can edit the monthly/yearly goals (both written and dream count)
        POST here to save the new goal information to the db
    '''
    def get(self):
        template_values = {}
        #initialize_global_stats()
        template_values['global_stats'] = get_global_stats()
        template = JINJA_ENVIRONMENT.get_template('editgoals.html')
        self.response.write(template.render(template_values))

    def post(self):
        global_stats = get_global_stats()
        yearly_dream_goal = get_integer_input(self.request, 'yearly_dream_goal', global_stats.yearly_dream_goal)
        month_goal = self.request.get('month_goal', global_stats.month_goal)
        year_goal = self.request.get('year_goal', global_stats.year_goal)
        global_stats.yearly_dream_goal = yearly_dream_goal
        global_stats.month_goal = month_goal
        global_stats.year_goal = year_goal
        global_stats.put()
        self.redirect('/')


def delete_report(date_string, update_global_stats=False):
    # TODO: get all report objects with a date greater than this one (but in the same year) and decrement their yearly snapshots by the amount in this report
    old_report_key = ndb.Key(Report, date_string)
    if update_global_stats:
        old_report = old_report_key.get()
        if old_report:
            global_stats = get_global_stats()
            global_stats.customers_this_year -= old_report.customers_today
            global_stats.dreams_this_year -= old_report.dreams
            global_stats.put()
    old_report_key.delete()


class DeleteReportHandler(webapp2.RequestHandler):
    def post(self, date_string):
        delete_report(date_string, update_global_stats=True)
        self.redirect('/')


class MainHandler(webapp2.RequestHandler):
    '''
    Main page: Links to creating a report or viewing all reports, or view most recent report?
    '''
    def get(self):
        template_values = {}
        # list of most recent reports
        # total number of dreams
        # average number of dreams per diem
        template_values['global_stats'] = get_global_stats()
        recent_reports = [x for x in Report.query().fetch(limit=10)]
        sorted_reports = sorted(recent_reports, key=lambda x: x.date, reverse=True)
        template_values['reports'] = sorted_reports
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


app = webapp2.WSGIApplication([
    (r'/reports', MainHandler),
    (r'/report/(\d\d\d\d-\d\d-\d\d)', ViewReportHandler),
    (r'/createreport', CreateReportHandler),
    (r'/previewreport', PreviewReportHandler),
    (r'/editgoals', EditGoalHandler),
    (r'/deletereport/(\d\d\d\d-\d\d-\d\d)', DeleteReportHandler),
    (r'/', MainHandler),
], debug=True)
