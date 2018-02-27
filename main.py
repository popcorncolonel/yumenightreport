import endpoints
import jinja2
import logging
import os
import webapp2

from google.appengine.ext import ndb
from datetime import datetime, date
import datetime
from report import Report


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True,
)


def is_past_2017(datetime_obj=None):
    if datetime_obj is None:
        datetime_obj = datetime.datetime.now()
    return datetime_obj.year > 2017


def get_working_days_left_in_year(date_obj):
    ''' date_obj must be a `date` object. Returns the number of days left in the year of date_obj '''
    end_year = datetime.date(date_obj.year, month=12, day=31)
    days_until_year_end = (end_year - date_obj).days
    # exclude sundays & mondays
    working_days_until_year_end = max(1, int((5./7.) * days_until_year_end))
    return working_days_until_year_end


class Goals(ndb.Model):
    # TODO: upon updating the month goal, set the month_goal's for all the reports
    #       this month to be the new goal
    yearly_dream_goal = ndb.IntegerProperty(default=0)
    year_goal = ndb.StringProperty(default="")
    month_goal = ndb.StringProperty(default="")

    def daily_dream_goal(self, working_days_left_in_year=None, datetime_obj=None):
        if datetime_obj is None:
            datetime_obj = datetime.datetime.now()
        if working_days_left_in_year is None:
            working_days_left_in_year = get_working_days_left_in_year(datetime_obj.date())
        if working_days_left_in_year == 0:
            return 0.
        dreams_remaining = max(0, self.yearly_dream_goal - Report.get_dreams_for_year(datetime_obj))
        return dreams_remaining / working_days_left_in_year

    @property
    def customers_this_year(self):
        return Report.get_customers_for_year(datetime.datetime.now().date())

    @property
    def dreams_this_year(self):
        return Report.get_dreams_for_year(datetime.datetime.now().date())

    @property
    def dreamers_this_year(self):
        return Report.get_dreamers_for_year(datetime.datetime.now().date())


class GlobalStats(ndb.Model):
    # TO BE REMOVED IN 2018
    '''
    Global information needed for all reports (like yearly dreamcount)
    '''
    dreamers_this_year = ndb.IntegerProperty(default=0)
    customers_this_year = ndb.IntegerProperty()
    dreams_this_year = ndb.IntegerProperty()  # these numbers are only for 2017.
    yearly_dream_goal = ndb.IntegerProperty()  # how many dreams would we like today?
    year_goal = ndb.StringProperty(default="")
    month_goal = ndb.StringProperty(default="")

    def daily_dream_goal(self, working_days_left_in_year=None, datetime_obj=None):
        if datetime_obj is None:
            datetime_obj = datetime.datetime.now()
        if working_days_left_in_year is None:
            working_days_left_in_year = get_working_days_left_in_year(datetime_obj.date())
        if working_days_left_in_year == 0:
            return 0.
        dreams_remaining = max(0, self.yearly_dream_goal - self.dreams_this_year)
        return dreams_remaining / working_days_left_in_year


def get_goals():
    goals_key = ndb.Key(Goals, "goals")
    goals = goals_key.get()
    if goals is None:
        return Goals(id="goals")
    return goals


def get_global_stats():
    if is_past_2017():
        return get_goals()
    global_stats_key = ndb.Key(GlobalStats, "global_stats")
    global_stats = global_stats_key.get()
    if global_stats is None:
        return GlobalStats(id="global_stats")
    return global_stats


def initialize_global_stats():
    global_stats = get_global_stats()
    global_stats.year_goal = "Say less"
    global_stats.month_goal = ""
    global_stats.yearly_dream_goal = 100000
    if not is_past_2017():
        global_stats.customers_this_year = 1000 #-182
        global_stats.dreams_this_year = 1000 #-135
    global_stats.put()
    return global_stats


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
        '''
        template_values = {}
        report_key = ndb.Key(Report, date_string)
        current_report = report_key.get()
        if current_report is None:
            raise endpoints.NotFoundException("No report found for {}".format(date_string))
        report_dict = create_report_dict_from_report_obj(current_report)
        today_datetime = datetime.datetime.now()
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
            end_time_obj = datetime.datetime.strptime(end_time, '%H:%M').time()  # deal w/ am/pm?
        else:
            end_time_obj = datetime.datetime.strptime(end_time, '%H%M').time()  # deal w/ am/pm?
    else:
        end_time_obj = None
    return end_time_obj


def get_date_obj(date):
    if date:
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
    else:
        date_obj = None
    return date_obj


def get_old_report(date):
    old_report = None
    if date is not None and date != '':
        old_report_key = ndb.Key(Report, date)
        old_report = old_report_key.get()
    return old_report


def _deprecated_populate_global_stats_snapshot(
    current_global_stats2017,
    old_report, # The report from the previous date
    overwriting_report, # The report we're overwriting
    new_report,
):
    '''
    Gets the current global stats variables from global_stats2017 if `old_report` is None,
    but gets the variables from the snapshot in `old_report` otherwise.
    Modifies the global snaps snapshot in `new_report` if values would be updated.
    
    this function sucks

    # TO BE REMOVED IN 2018
    '''
    if old_report is None:
        new_report.month_goal = current_global_stats2017.month_goal
        new_report.year_goal = current_global_stats2017.year_goal
        new_report.yearly_dream_goal = current_global_stats2017.yearly_dream_goal
        new_report.dreams_this_year = current_global_stats2017.dreams_this_year
        new_report.customers_this_year = current_global_stats2017.customers_this_year
        if new_report.date is not None:
            new_report.daily_dream_goal = current_global_stats2017.daily_dream_goal(get_working_days_left_in_year(new_report.date.date()))
        else:
            new_report.daily_dream_goal = current_global_stats2017.daily_dream_goal()
    else:
        new_report.month_goal = old_report.month_goal
        new_report.year_goal = old_report.year_goal
        new_report.yearly_dream_goal = old_report.yearly_dream_goal
        new_report.dreams_this_year = old_report.dreams_this_year or current_global_stats2017.dreams_this_year
        new_report.customers_this_year = old_report.customers_this_year or current_global_stats2017.customers_this_year
        if old_report.dreams:
            new_report.dreams_this_year -= old_report.dreams
        if old_report.customers_today:
            new_report.customers_this_year -= old_report.customers_today
        new_report.daily_dream_goal = old_report.daily_dream_goal

    if new_report.get_dreams() is not None:
        new_report.dreams_this_year += new_report.get_dreams()
    if new_report.get_customers_today() is not None:
        new_report.customers_this_year += new_report.get_customers_today()
    if overwriting_report is not None and overwriting_report != old_report:
        if overwriting_report.get_dreams():
            new_report.dreams_this_year -= overwriting_report.get_dreams()
        if overwriting_report.get_customers_today():
            new_report.customers_this_year -= overwriting_report.get_customers_today()


def _deprecated_populate_achievement_rate(report):
    if report.dreams is None:
        report.achievement_rate = None
    else:
        if report.get_daily_dream_goal() == 0:
            report.achievement_rate = 100.
        else:
        	report.achievement_rate = (report.dreams / float(report.get_daily_dream_goal())) * 100


def _deprecated_update_global_stats_with_report_info(report, old_report, overwriting_report, current_global_stats):
    if not report.is_past_2017() and report.is_finalized():
        if old_report is not None:
            if old_report.customers_today:
                current_global_stats.customers_this_year -= old_report.get_customers_today()
            if old_report.dreams:
                current_global_stats.dreams_this_year -= old_report.get_dreams()
        if overwriting_report is not None:
            if old_report is None or old_report.date_string != overwriting_report.date_string:
                if overwriting_report.customers_today:
                    current_global_stats.customers_this_year -= overwriting_report.get_customers_today()
                if overwriting_report.dreams:
                    current_global_stats.dreams_this_year -= overwriting_report.get_dreams()
        current_global_stats.customers_this_year += report.get_customers_today()
        current_global_stats.dreams_this_year += report.get_dreams()
        print("DBG: updating global stats -- report dreams == {}".format(report.get_dreams()))
        print("DBG: updating global stats -- dreams == {}".format(current_global_stats.dreams_this_year))
        current_global_stats.put()


def _populate_dinner_totals(report):
    if report.lunch_customers_today is not None and report.customers_today is not None:
        report.dinner_customers_today = report.customers_today - report.lunch_customers_today
    if report.lunch_dreams is not None and report.dreams is not None:
        report.dinner_dreams = report.dreams - report.lunch_dreams
    if report.lunch_dreamers is not None and report.dreamers is not None:
        report.dinner_dreamers = report.dreamers - report.lunch_dreamers


def _populate_report_fields_from_request(report, request):
    # Parse and populate date/time fields
    date_string = request.get('date', '')
    end_time = request.get('end_time', '')
    report.date = get_date_obj(date_string)
    report.end_time = get_time_obj(end_time)

    # They want to input lunch and total. So we compute dinner manually.
    report.lunch_customers_today = get_integer_input(request, 'lunch_customers_today')
    report.customers_today = get_integer_input(request, 'customers_today')
    report.lunch_dreams = get_integer_input(request, 'lunch_dreams')
    report.dreams = get_integer_input(request, 'dreams')
    report.lunch_dreamers = get_integer_input(request, 'lunch_dreamers')
    report.dreamers = get_integer_input(request, 'dreamers')

    report.working_members = request.get('working_members', '')
    report.supporting_members = request.get('supporting_members', '')
    report.visiting_members = request.get('visiting_members', '')

    report.total_bowls = get_integer_input(request, 'total_bowls')
    report.total_cups = get_integer_input(request, 'total_cups')
    report.chopsticks_missing = get_integer_input(request,'chopsticks_missing')
    report.money_off_by = get_integer_input(request, 'money_off_by')
    report.positive_cycle = get_integer_input(request, 'positive_cycle')
    report.misc_notes = request.get('misc_notes', '')

def get_report_from_request(request, update_global_stats, prev_date=None):
    report = Report(id=request.get('date', ''))
    _populate_report_fields_from_request(report, request)
    _populate_dinner_totals(report)

    # Snapshot the goals. Maybe this should eventually be removed but it's pretty easy logic since the goals are fairly static.
    if report.is_past_2017():
        current_goals = get_global_stats()
        report.month_goal = current_goals.month_goal
        report.year_goal = current_goals.year_goal
        report.yearly_dream_goal = current_goals.yearly_dream_goal
    else:
        # overwriting_report is the report we're overwriting by saving this report
        overwriting_report = get_old_report(report.date_string)
        # old_report is the report we're modifying, if editing for a date that currently has a report for it
        if prev_date:
            old_report = get_old_report(prev_date)
        else:
            old_report = None
        current_global_stats = get_global_stats()
        _deprecated_populate_global_stats_snapshot(current_global_stats, old_report, overwriting_report, report)
        _deprecated_populate_achievement_rate(report)
        if update_global_stats:
            _deprecated_update_global_stats_with_report_info(report, old_report, overwriting_report, current_global_stats)
    return report

def create_report_dict_from_report_obj(current_report):
    # TODO: optimize -- if you call "get_...()" twice it's twice the database calls!
    report_dict = {
        'month_goal': current_report.month_goal if current_report.month_goal is not None else '',
        'year_goal': current_report.year_goal if current_report.year_goal is not None else '',

        'datetime_obj': current_report.date,
        'date': current_report.date.strftime('%Y-%m-%d') if current_report.date is not None else '',
        'date_string': current_report.date.strftime('%Y-%m-%d') if current_report.date is not None else '',
        'readable_date_string': current_report.readable_date_string if current_report.readable_date_string is not None else '',

        'lunch_customers_today': current_report.lunch_customers_today if current_report.lunch_customers_today is not None else '',
        'dinner_customers_today': current_report.dinner_customers_today if current_report.dinner_customers_today is not None else '',
        'lunch_dreams': current_report.lunch_dreams if current_report.lunch_dreams is not None else '',
        'dinner_dreams': current_report.dinner_dreams if current_report.dinner_dreams is not None else '',
        'lunch_dreamers': current_report.lunch_dreamers if current_report.lunch_dreamers is not None else '',
        'dinner_dreamers': current_report.dinner_dreamers if current_report.dinner_dreamers is not None else '',

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
        'customers_today': current_report.get_customers_today() if current_report.get_customers_today() is not None else '',
        'dreams': current_report.get_dreams() if current_report.get_dreams() is not None else '',
        'dreamers': current_report.get_dreamers() if current_report.get_dreamers() is not None else '',
        'daily_dream_goal': current_report.get_daily_dream_goal() or '',
        'yearly_dream_goal': current_report.yearly_dream_goal or '',
        'customers_this_year': current_report.get_customers_this_year() if current_report.get_customers_this_year() is not None else '',
        'dreams_this_year': current_report.get_dreams_this_year() if current_report.get_dreams_this_year() is not None else '',
        'dreamers_this_year': current_report.get_dreamers_this_year() or '',
        'perfect_money_marathon': current_report.get_perfect_money_marathon()  if current_report.get_perfect_money_marathon() is not None else  '',
        'achievement_rate': '{:.2f}%'.format(current_report.get_achievement_rate()) if \
                current_report.get_achievement_rate() is not None else '',
        'is_past_2017': current_report.is_past_2017() or '',
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
        if date_string == '':
            date_string = (datetime.datetime.now() - datetime.timedelta(hours=12)).strftime('%Y-%m-%d')
        current_report_key = ndb.Key(Report, date_string)
        request_report = get_report_from_request(self.request, update_global_stats=False)
        if date_string:
            past_report = current_report_key.get()
            logging.info('past_report: {}'.format(past_report))
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
        print('DBG: posting new report: {}'.format(new_report))
        new_report.put()
        #if old_date_string != "" and old_date_string is not None:
        #    if old_date_string != new_report.date_string:
        #        delete_report(old_date_string)
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
        report_dict = create_report_dict_from_report_obj(current_report)
        template_values['global_stats'] = get_global_stats()
        template_values['report'] = report_dict
        template_values['preview'] = True
        template_values['hidetitleimg'] = True
        template_values['old_date_string'] = old_date_string
        template = JINJA_ENVIRONMENT.get_template('report.html')
        self.response.write(template.render(template_values))


class StatsHandler(webapp2.RequestHandler):
    '''
    Handler to view statistics about the reports. GET only.
    '''
    def get(self):
        this_year = datetime.datetime.now().year
        this_month = datetime.datetime.now().month
        january_1_this_year = datetime.datetime.strptime('01/01/{}'.format(this_year), '%m/%d/%Y')
        december_31_this_year = datetime.datetime.strptime('12/31/{}'.format(this_year), '%m/%d/%Y')
        reports_this_year = Report.query(ndb.AND(
            Report.date >= january_1_this_year,
            Report.date <= december_31_this_year,
        ))
        def make_dict_for_month(month):
            month_reports = [x for x in reports_this_year if x.date.month == month and x.is_finalized()]
            return {
                'total_dreams': sum(report.get_dreams() for report in month_reports),
                'total_dreamers': sum(report.get_dreamers() for report in month_reports),
                'total_customers': sum(report.get_customers_today() for report in month_reports),
                'average_dreams': sum(report.get_dreams() for report in month_reports) / float(len(month_reports)),
                'average_dreamers': sum(report.get_dreamers() for report in month_reports) / float(len(month_reports)),
                'average_customers': sum(report.get_customers_today() for report in month_reports) / float(len(month_reports)),
                'average_dream_achievement_rate': "{:.2f}".format(
                    sum(report.get_achievement_rate() for report in month_reports) / float(len(month_reports))),
                'num_reports': len(month_reports),
                'month_string': datetime.datetime.strptime('2018-{:02d}-01'.format(month), '%Y-%m-%d').strftime('%B'),
            }
        monthly_stats_list = [make_dict_for_month(month_num) for month_num in range(this_month, 0, -1)]
        template_values = {}
        template_values['global_stats'] = get_global_stats()
        template_values['monthly_stats_list'] = monthly_stats_list
        template = JINJA_ENVIRONMENT.get_template('stats.html')
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
        goals_obj = get_global_stats()
        yearly_dream_goal = get_integer_input(self.request, 'yearly_dream_goal', goals_obj.yearly_dream_goal)
        month_goal = self.request.get('month_goal', goals_obj.month_goal)
        year_goal = self.request.get('year_goal', goals_obj.year_goal)
        goals_obj.yearly_dream_goal = yearly_dream_goal
        goals_obj.month_goal = month_goal
        goals_obj.year_goal = year_goal
        goals_obj.put()
        self.redirect('/')


class DeleteReportHandler(webapp2.RequestHandler):
    def post(self, date_string):
        old_report_key = ndb.Key(Report, date_string)
        if old_report_key.get() is not None:
            old_report_key.delete()
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
        recent_reports = [x for x in Report.query().order(-Report.date).fetch(limit=20)]
        sorted_reports = sorted(recent_reports, key=lambda x: x.date, reverse=True)
        # ignore incomplete reports
        sorted_reports = [report for report in sorted_reports if report.is_finalized()]
        template_values['reports'] = sorted_reports
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


app = webapp2.WSGIApplication([
    (r'/reports', MainHandler),
    (r'/report/(\d\d\d\d-\d\d-\d\d)', ViewReportHandler),
    (r'/createreport', CreateReportHandler),
    (r'/previewreport', PreviewReportHandler),
    (r'/stats', StatsHandler),
    (r'/editgoals', EditGoalHandler),
    (r'/deletereport/(\d\d\d\d-\d\d-\d\d)', DeleteReportHandler),
    (r'/', MainHandler),
], debug=True)

