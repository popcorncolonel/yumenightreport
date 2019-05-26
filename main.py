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


def get_working_days_left_in_year(date_obj):
    ''' date_obj must be a `date` object. Returns the number of days left in the year of date_obj '''
    end_year = datetime.date(date_obj.year, month=12, day=31)
    days_until_year_end = (end_year - date_obj).days
    # Exclude sundays & mondays & holidays
    num_holidays_approx = 4
    working_days_until_year_end = int((5./7.) * days_until_year_end) - num_holidays_approx
    # Clamp between [1, infty)
    working_days_until_year_end = max(1, working_days_until_year_end)
    return working_days_until_year_end


def get_reports_this_year(force_datetime=None):
    if force_datetime is not None and len(force_datetime) > 0:
        this_datetime = force_datetime
    else:
        this_datetime = datetime.datetime.now()
    this_year = this_datetime.year
    this_month = this_datetime.month
    january_1_this_year = datetime.datetime.strptime('01/01/{}'.format(this_year), '%m/%d/%Y')
    december_31_this_year = datetime.datetime.strptime('12/31/{}'.format(this_year), '%m/%d/%Y')
    reports_this_year = [report for report in Report.query(ndb.AND(
        Report.date >= january_1_this_year,
        Report.date <= december_31_this_year,
    )) if report.is_finalized()]
    return reports_this_year


def get_reports_this_month(month_num):
    this_datetime = datetime.datetime.now()
    this_year = this_datetime.year
    month_beginning = datetime.datetime.strptime('{:02d}/01/{:04d}'.format(month_num, this_year), '%m/%d/%Y')
    if month_num < 12:
        next_month_beginning = datetime.datetime.strptime('{:02d}/01/{:04d}'.format(month_num + 1, this_year), '%m/%d/%Y')
    else:
        next_month_beginning = datetime.datetime.strptime('01/01/{}'.format(this_year + 1), '%m/%d/%Y')
    reports_this_month = [report for report in Report.query(ndb.AND(
        Report.date >= month_beginning,
        Report.date < next_month_beginning,
    )) if report.is_finalized()]
    return reports_this_month


def calculate_dream_dicts(month_reports, goal_dict):
    '''
    * {Lunch, Dinner} x {Dreams, Dreamers, Customers} achievement rates, given the goals in `goal_dict`.
    * goal_dict example: {'lunch_dreams': 50, 'lunch_dreamers': '30', 'lunch_customers': 80}, ...}
    '''
    actual_dict = {key: 0 for key in goal_dict}
    num_lunch_reports = 0
    num_dinner_reports = 0
    for report in month_reports:
        if report.lunch_customers_today > 0 and report.lunch_dreamers > 0 and report.lunch_dreams > 0:
            num_lunch_reports += 1
            actual_dict['lunch_customers_today'] += report.lunch_customers_today
            actual_dict['lunch_dreamers'] += report.lunch_dreamers
            actual_dict['lunch_dreams'] += report.lunch_dreams
        if report.dinner_customers_today > 0 and report.dinner_dreamers > 0 and report.dinner_dreams > 0:
            num_dinner_reports += 1
            actual_dict['dinner_customers_today'] += report.dinner_customers_today
            actual_dict['dinner_dreamers'] += report.dinner_dreamers
            actual_dict['dinner_dreams'] += report.dinner_dreams

    expected_dict = {}
    for key in goal_dict:
        if key.startswith('lunch'):
            expected_dict[key] = num_lunch_reports * goal_dict[key]
        if key.startswith('dinner'):
            expected_dict[key] = num_dinner_reports * goal_dict[key]
    return (actual_dict, expected_dict)


class Goals(ndb.Model):
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


def get_goals():
    goals_key = ndb.Key(Goals, "goals")
    goals = goals_key.get()
    if goals is None:
        return Goals(id="goals")
    return goals


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
        goals = get_goals()
        template_values['goals'] = goals
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
    end_time_dishwasher = request.get('end_time_dishwasher', '')
    end_time_host = request.get('end_time_host', '')
    end_time_kitchen2 = request.get('end_time_kitchen2', '')
    end_time_kitchen = request.get('end_time_kitchen', '')
    report.date = get_date_obj(date_string)
    report.end_time_dishwasher = get_time_obj(end_time_dishwasher)
    report.end_time_host = get_time_obj(end_time_host)
    report.end_time_kitchen2 = get_time_obj(end_time_kitchen2)
    report.end_time_kitchen = get_time_obj(end_time_kitchen)

    # They want to input lunch and total. So we compute dinner manually.
    report.lunch_customers_today = get_integer_input(request, 'lunch_customers_today')
    report.customers_today = get_integer_input(request, 'customers_today')
    report.lunch_dreams = get_integer_input(request, 'lunch_dreams')
    report.dreams = get_integer_input(request, 'dreams')
    report.lunch_dreamers = get_integer_input(request, 'lunch_dreamers')
    report.dreamers = get_integer_input(request, 'dreamers')

    report.working_dishwasher = request.get('working_dishwasher', '')
    report.working_host = request.get('working_host', '')
    report.working_kitchen2 = request.get('working_kitchen2', '')
    report.working_kitchen = request.get('working_kitchen', '')
    report.supporting_members = request.get('supporting_members', '')
    report.visiting_members = request.get('visiting_members', '')

    report.total_bowls = get_integer_input(request, 'total_bowls')
    report.total_cups = get_integer_input(request, 'total_cups')
    report.chopsticks_missing = get_integer_input(request,'chopsticks_missing')
    report.money_off_by = get_integer_input(request, 'money_off_by')
    report.positive_cycle = get_integer_input(request, 'positive_cycle')
    report.misc_notes = request.get('misc_notes', '')

def get_report_from_request(request, prev_date=None):
    report = Report(id=request.get('date', ''))
    _populate_report_fields_from_request(report, request)
    _populate_dinner_totals(report)

    # Snapshot the goals. Maybe this should eventually be removed but it's pretty easy logic since the goals are fairly static.
    current_goals = get_goals()
    report.month_goal = current_goals.month_goal
    report.year_goal = current_goals.year_goal
    report.yearly_dream_goal = current_goals.yearly_dream_goal
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

        'working_dishwasher': current_report.working_dishwasher if current_report.working_dishwasher is not None else '',
        'working_host': current_report.working_host if current_report.working_host is not None else '',
        'working_kitchen2': current_report.working_kitchen2 if current_report.working_kitchen2 is not None else '',
        'working_kitchen': current_report.working_kitchen if current_report.working_kitchen is not None else '',
        'supporting_members': current_report.supporting_members if current_report.supporting_members is not None else '',
        'visiting_members': current_report.visiting_members if current_report.visiting_members is not None else '',
        'end_time': current_report.get_end_time().strftime('%H:%M') if current_report.get_end_time() is not None else '',
        'end_time_dishwasher': current_report.end_time_dishwasher.strftime('%H:%M') if current_report.end_time_dishwasher is not None else '',
        'end_time_host': current_report.end_time_host.strftime('%H:%M') if current_report.end_time_host is not None else '',
        'end_time_kitchen2': current_report.end_time_kitchen2.strftime('%H:%M') if current_report.end_time_kitchen2 is not None else '',
        'end_time_kitchen': current_report.end_time_kitchen.strftime('%H:%M') if current_report.end_time_kitchen is not None else '',
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
        request_report = get_report_from_request(self.request)
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
        template_values['goals'] = get_goals()
        template_values['hidetitleimg'] = True
        self.response.write(template.render(template_values))

    def post(self):
        # get stuff from POST request
        # create a new Report object and save it to ndb
        old_date_string = self.request.get('old_date_string', None)
        new_report = get_report_from_request(self.request, prev_date=old_date_string)
        new_report.put()
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
        current_report = get_report_from_request(self.request, prev_date=old_date_string)
        report_dict = create_report_dict_from_report_obj(current_report)
        template_values['goals'] = get_goals()
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

    def _make_monthly_stats_list(self, monthly_stats_list, reports_this_year):
        for i in range(len(monthly_stats_list)):
            monthly_stats_list[i] = {
                'total_lunch_dreams': 0,
                'total_dinner_dreams': 0,
                'total_lunch_dreamers': 0,
                'total_dinner_dreamers': 0,
                'total_lunch_customers': 0,
                'total_dinner_customers': 0,

                'lunch_denom': 0,
                'dinner_denom': 0,
                'denom': 0,
            }
        for report in reports_this_year:
            report.report_list = reports_this_year
            monthly_stats_list[report.date.month - 1]['total_lunch_dreams'] += report.lunch_dreams
            monthly_stats_list[report.date.month - 1]['total_dinner_dreams'] += report.dinner_dreams
            monthly_stats_list[report.date.month - 1]['total_lunch_dreamers'] += report.lunch_dreamers
            monthly_stats_list[report.date.month - 1]['total_dinner_dreamers'] += report.dinner_dreamers
            monthly_stats_list[report.date.month - 1]['total_lunch_customers'] += report.lunch_customers_today
            monthly_stats_list[report.date.month - 1]['total_dinner_customers'] += report.dinner_customers_today
            monthly_stats_list[report.date.month - 1]['denom'] += 1
            if report.lunch_dreams != 0 or report.lunch_dreamers != 0 or report.lunch_customers_today != 0:
                monthly_stats_list[report.date.month - 1]['lunch_denom'] += 1
            if report.dinner_dreams != 0 or report.dinner_dreamers != 0 or report.dinner_customers_today != 0:
                monthly_stats_list[report.date.month - 1]['dinner_denom'] += 1
        for report in reports_this_year:
            month_dict = monthly_stats_list[report.date.month - 1]
            denom = float(month_dict['denom'])
            if 'average_dream_achievement_rate' not in month_dict:
                month_dict['average_dream_achievement_rate'] = 0.0
            month_dict['average_dream_achievement_rate'] += report.get_achievement_rate() / denom
        for i, month_dict in enumerate(monthly_stats_list):
            month_dict['average_dinner_dreams'] = '{:.2f}'.format(month_dict['total_dinner_dreams'] / max(1, month_dict['dinner_denom']))
            month_dict['average_dinner_dreamers'] = '{:.2f}'.format(month_dict['total_dinner_dreamers'] / max(1, month_dict['dinner_denom']))
            month_dict['average_dinner_customers'] = '{:.2f}'.format(month_dict['total_dinner_customers'] / max(1, month_dict['dinner_denom']))

            month_dict['average_lunch_dreams'] = '{:.2f}'.format(month_dict['total_lunch_dreams'] / max(1, month_dict['lunch_denom']))
            month_dict['average_lunch_dreamers'] = '{:.2f}'.format(month_dict['total_lunch_dreamers'] / max(1, month_dict['lunch_denom']))
            month_dict['average_lunch_customers'] = '{:.2f}'.format(month_dict['total_lunch_customers'] / max(1, month_dict['lunch_denom']))

            if 'average_dream_achievement_rate' in month_dict:
                month_dict['average_dream_achievement_rate'] = "{:.2f}".format(month_dict['average_dream_achievement_rate'])
            else:
                month_dict['average_dream_achievement_rate'] = 0.0
            month_dict['num_reports'] = month_dict['denom']
            month_dict['month_string'] = datetime.datetime.strptime('2018-{:02d}-01'.format(i + 1), '%Y-%m-%d').strftime('%B'),

    def _make_dict_for_month(self, month, reports_this_year):
        month_reports = [x for x in reports_this_year if x.date.month == month and x.is_finalized()]
        denom = len(month_reports) if len(month_reports) > 0 else 1
        sum_lunch_dreams = 0
        sum_lunch_dreamers = 0
        sum_lunch_customers = 0
        sum_dinner_dreams = 0
        sum_dinner_dreamers = 0
        sum_dinner_customers = 0
        for report in month_reports:
            sum_lunch_dreams += report.lunch_dreams
            sum_dinner_dreams += report.dinner_dreams
            sum_lunch_dreamers += report.lunch_dreamers
            sum_dinner_dreamers += report.dinner_dreamers
            sum_lunch_customers += report.lunch_customers_today
            sum_dinner_customers += report.dinner_customers_today
        return {
            'total_lunch_dreams': sum_lunch_dreams,
            'total_dinner_dreams': sum_dinner_dreams,
            'total_lunch_dreamers': sum_lunch_dreamers,
            'total_dinner_dreamers': sum_dinner_dreamers,
            'total_lunch_customers': sum_lunch_customers,
            'total_dinner_customers': sum_dinner_customers,

            'average_lunch_dreams': '{:.2f}'.format(sum_lunch_dreams / float(denom)),
            'average_dinner_dreams': '{:.2f}'.format(sum_dinner_dreams / float(denom)),
            'average_lunch_dreamers': '{:.2f}'.format(sum_lunch_dreamers / float(denom)),
            'average_dinner_dreamers': '{:.2f}'.format(sum_dinner_dreamers / float(denom)),
            'average_lunch_customers': '{:.2f}'.format(sum_lunch_customers / float(denom)),
            'average_dinner_customers': '{:.2f}'.format(sum_dinner_customers / float(denom)),

            'average_dream_achievement_rate': "{:.2f}".format(
                sum(report.get_achievement_rate() for report in month_reports) / float(denom)),
            'num_reports': len(month_reports),
            'month_string': datetime.datetime.strptime('2018-{:02d}-01'.format(month), '%Y-%m-%d').strftime('%B'),
        }

    def _make_weekly_dict(self, reports_this_year, lunch_or_dinner):
        '''
        Returns a dict with keys = "Tuesday", ..., "Saturday"
                            vals = [(date, customer count), ...] pairs
        i.e. dict['Tuesday'] = [(Jan 01, 98), (Jan 08, 90), ...]

        Guaranteed to be fully populated with every week up until today's date.
        `lunch_or_dinner` must be 'lunch' or 'dinner'.
        '''
        assert lunch_or_dinner in {'lunch', 'dinner'}
        open_days = {'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'}
        d = {day: [] for day in open_days}
        # Go back in time until we see the first saturday in reverse order (i.e. a full complete week tuesday-saturday)
        found_first_saturday = False
        for report in sorted(reports_this_year, key=lambda x: x.date, reverse=True):
            weekday = report.date.strftime("%A")
            if not found_first_saturday and weekday != 'Saturday':
                continue
            found_first_saturday = True
            if weekday in open_days:
                # If we missed a week, add in a dummy '0' report
                if len(d[weekday]) > 0:
                    prev_date = d[weekday][-1][0]
                    # Previously added date could be, e.g. 7/17/18 and current date = 7/10/18
                    while (prev_date - report.date) > datetime.timedelta(weeks=1):
                        d[weekday].append((prev_date - datetime.timedelta(weeks=1), 0))
                        prev_date = d[weekday][-1][0]
                if lunch_or_dinner == 'lunch':
                    d[weekday].append((report.date, report.lunch_customers_today))
                else:
                    d[weekday].append((report.date, report.dinner_customers_today))
        tuesday_len = len(d['Tuesday'])
        for day in ['Wednesday', 'Thursday', 'Friday', 'Saturday']:
            while len(d[day]) < tuesday_len:
                d[day].append((datetime.datetime.now(), ""))
        return d

    def get(self):
        force_datetime = self.request.get_all('force_datetime')
        this_datetime = datetime.datetime.now()
        print('force_datetime: {}'.format(force_datetime))
        if force_datetime is not None and len(force_datetime) > 0:
            force_datetime = force_datetime[0]
            if len(force_datetime) > 0:
                date_fmt = '%Y-%m-%d'  # 2019-01-14 
                force_datetime = datetime.datetime.strptime(force_datetime, date_fmt)
        reports_this_year = get_reports_this_year(force_datetime)
        this_year = this_datetime.year
        this_month = this_datetime.month
        january_1_this_year = datetime.datetime.strptime('01/01/{}'.format(this_year), '%m/%d/%Y')
        december_31_this_year = datetime.datetime.strptime('12/31/{}'.format(this_year), '%m/%d/%Y')
        reports_this_year = [report for report in Report.query(ndb.AND(
            Report.date >= january_1_this_year,
            Report.date <= december_31_this_year,
        )) if report.is_finalized()]
        #monthly_stats_list = [self._make_dict_for_month(month_num, reports_this_year) for month_num in range(this_month, 0, -1)]
        monthly_stats_list = [{} for month_num in range(this_month, 0, -1)]
        self._make_monthly_stats_list(monthly_stats_list, reports_this_year)
        template_values = {}
        template_values['goals'] = get_goals()
        template_values['monthly_stats_list'] = monthly_stats_list
        weekly_lunch_stats_dict = self._make_weekly_dict(reports_this_year, 'lunch')
        weekly_dinner_stats_dict = self._make_weekly_dict(reports_this_year, 'dinner')
        weekly_lunch_stats_matrix = list(zip(
            weekly_lunch_stats_dict['Tuesday'],
            weekly_lunch_stats_dict['Wednesday'],
            weekly_lunch_stats_dict['Thursday'],
            weekly_lunch_stats_dict['Friday'],
            weekly_lunch_stats_dict['Saturday'],
        ))
        weekly_dinner_stats_matrix = list(zip(
            weekly_dinner_stats_dict['Tuesday'],
            weekly_dinner_stats_dict['Wednesday'],
            weekly_dinner_stats_dict['Thursday'],
            weekly_dinner_stats_dict['Friday'],
            weekly_dinner_stats_dict['Saturday'],
        ))
        for i, week in enumerate(weekly_lunch_stats_matrix):
            print(week)
            total_customers = sum(day[1] for day in week if type(day[1]) == int)
            weekly_lunch_stats_matrix[i] = [x for x in week] + [total_customers]
        for i, week in enumerate(weekly_dinner_stats_matrix):
            print(week)
            total_customers = sum(day[1] for day in week if type(day[1]) == int)
            weekly_dinner_stats_matrix[i] = [x for x in week] + [total_customers]
        template_values['weekly_lunch_stats_matrix'] = weekly_lunch_stats_matrix
        template_values['weekly_dinner_stats_matrix'] = weekly_dinner_stats_matrix
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
        template_values['goals'] = get_goals()
        template = JINJA_ENVIRONMENT.get_template('editgoals.html')
        self.response.write(template.render(template_values))

    def post(self):
        goals_obj = get_goals()
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


class DreamCalculatorHandler(webapp2.RequestHandler):
    '''
    Handler to . TODO: write this
        GET here to ...
        POST here to ...
    '''
    def get(self):
        request = self.request
        # If we have any of the proper fields (dream/lunch_*s), display them and the achievement dict, along with a back button.
        # Otherwise, display the static page which will post to this endpoint indicating which month the user wants and the appropriate goals.
        template_values = {}
        this_datetime = datetime.datetime.now()
        if (
            request.get('month', None) is not None and
            request.get('lunch_customers_today', None) is not None and
            request.get('lunch_dreams', None) is not None and
            request.get('lunch_dreamers', None) is not None and
            request.get('dinner_customers_today', None) is not None and
            request.get('dinner_dreams', None) is not None and
            request.get('dinner_dreamers', None) is not None
        ):
            month_num = int(request.get('month', None))
            month_datetime = datetime.datetime.strptime('{:02d}/01/{:04d}'.format(month_num, this_datetime.year), '%m/%d/%Y')
            template_values['month_display'] = month_datetime.strftime('%B %Y')
            reports_this_month = get_reports_this_month(month_num)
            goal_dict = {
                'lunch_customers_today': int(request.get('lunch_customers_today')),
                'lunch_dreams': int(request.get('lunch_dreams')),
                'lunch_dreamers': int(request.get('lunch_dreamers')),
                'dinner_customers_today': int(request.get('dinner_customers_today')),
                'dinner_dreams': int(request.get('dinner_dreams')),
                'dinner_dreamers': int(request.get('dinner_dreamers')),
            }
            (actual_dict, expected_dict) = calculate_dream_dicts(reports_this_month, goal_dict)

            for key in actual_dict:
                template_values['goal_{}'.format(key)] = goal_dict[key]
                template_values['actual_{}'.format(key)] = actual_dict[key]
                template_values['expected_{}'.format(key)] = expected_dict[key]
                if expected_dict[key] != 0:
                    template_values['percent_{}'.format(key)] = "{:.2f}".format(100 * float(actual_dict[key]) / expected_dict[key])
                else:
                    template_values['percent_{}'.format(key)] = "100"
        else:
            # First pass of this page - which month is the user requesting?
            template_values['max_month'] = this_datetime.month

        template = JINJA_ENVIRONMENT.get_template('dreamcalculator.html')
        self.response.write(template.render(template_values))


class MainHandler(webapp2.RequestHandler):
    '''
    Main page: Links to creating a report or viewing all reports, or view most recent report?
    '''
    def get(self):
        template_values = {}
        # list of most recent reports
        # total number of dreams
        # average number of dreams per diem
        template_values['goals'] = get_goals()
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
    (r'/dreamcalculator', DreamCalculatorHandler),
    (r'/deletereport/(\d\d\d\d-\d\d-\d\d)', DeleteReportHandler),
    (r'/', MainHandler),
], debug=True)

