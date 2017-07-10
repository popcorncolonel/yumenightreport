import endpoints
import jinja2
import os
import webapp2

from google.appengine.ext import ndb
from datetime import datetime


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True
)


class GlobalStats(ndb.Model):
    '''
    Global information needed for all reports (like yearly dreamcount)
    '''
    num_customers_this_year = ndb.IntegerProperty()
    num_dreams_this_year = ndb.IntegerProperty()
    daily_dream_goal = ndb.IntegerProperty()  # how many dreams would we like today?
    year_goal = ndb.StringProperty()


class Report(ndb.Model):
    '''
    Information for the daily report
    '''
    date = ndb.DateTimeProperty()
    month_goal = ndb.StringProperty()
    num_customers_today = ndb.IntegerProperty()
    num_dreamers = ndb.IntegerProperty()
    num_dreams = ndb.IntegerProperty()
       
    """ Global stats snapshot """
    year_goal = ndb.StringProperty()
    num_customers_this_year = ndb.IntegerProperty()
    num_dreams_this_year = ndb.IntegerProperty()
    daily_dream_goal = ndb.IntegerProperty()  # how many dreams would we like today?

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


    @property
    def datestring(self):
        ''' 2017-06-13 '''
        if self.date:
            return self.date.strftime('%Y-%m-%d')
        else:
            return None

    @property
    def readable_datestring(self):
        ''' Tuesday June 13, 2017 '''
        if self.date:
            return self.date.strftime('%A %b %d, %Y')
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
    def get(self, datestring):
        '''
        Get corresponding report from datestring, if it exists. if not, 404
        We should allow editing of a report, which takes you to CreateReportHandler with all the info already pre-filled in
        '''
        template_values = {}

        report_key = ndb.Key(Report, datestring)
        curr_report = report_key.get()
        if curr_report is None:
            raise endpoints.NotFoundException("No report found for {}".format(datestring))

        report_dict = create_report_dict_from_report_obj(curr_report)

        template_values['report'] = report_dict
        today_datetime = datetime.now()
        template_values['today_datestring'] = today_datetime.strftime('%Y-%m-%d')
        
        template = JINJA_ENVIRONMENT.get_template('report.html')
        self.response.write(template.render(template_values))


def get_integer_input(request, key):
    val = request.get(key, None)
    if val is not None and val != '':
        int_val = int(val)
    else:
        int_val = None
    return int_val



def get_report_from_request(request, update_global_stats=True):
    date = request.get('date', '')
    month_goal = request.get('month_goal', '')
    num_customers_today = get_integer_input(request, 'num_cust_today')
    num_dreamers = get_integer_input(request, 'num_dreamers')
    num_dreams = get_integer_input(request, 'num_dreams')
    working_members = request.get('working_members', '')
    supporting_members = request.get('supporting_members', '')
    visiting_members = request.get('visiting_members', '')
    end_time = request.get('end_time', '')
    total_bowls = get_integer_input(request, 'total_bowls')
    total_cups = get_integer_input(request, 'total_cups')
    chopsticks_missing = get_integer_input(request,'chopsticks_missing')
    money_off_by = get_integer_input(request, 'money_off_by')
    positive_cycle = get_integer_input(request, 'pos_cycle')
    
    if end_time:
        if ':' in end_time:
            end_time_obj = datetime.strptime(end_time, '%H:%M').time()  # deal w/ am/pm?
        else:
            end_time_obj = datetime.strptime(end_time, '%H%M').time()  # deal w/ am/pm?
    else:
        end_time_obj = None
    if date:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
    else:
        date_obj = None

    global_stats_key = ndb.Key(GlobalStats, "global_stats")
    curr_global_stats = global_stats_key.get()

    if date != '':
        old_report_key = ndb.Key(Report, date)
        old_report = old_report_key.get()
    else:
        old_report = None
    year_goal = curr_global_stats.year_goal
    if old_report is None:

        #curr_global_stats.num_dreams_this_year = 1000
        #curr_global_stats.num_customers_this_year = 1000
        #curr_global_stats.daily_dream_goal = 100
        #curr_global_stats.put()
        daily_dream_goal = curr_global_stats.daily_dream_goal
        num_dreams_this_year = curr_global_stats.num_dreams_this_year
        num_customers_this_year = curr_global_stats.num_customers_this_year
    else:
        if update_global_stats:
            curr_global_stats.num_customers_this_year = curr_global_stats.num_customers_this_year - old_report.num_customers_today
            curr_global_stats.num_dreams_this_year = curr_global_stats.num_dreams_this_year - old_report.num_dreams
        daily_dream_goal = old_report.daily_dream_goal or 100
        num_dreams_this_year = old_report.num_dreams_this_year + (num_dreams - old_report.num_dreams)
        num_customers_this_year = old_report.num_customers_this_year  + (num_customers_today - old_report.num_customers_today) 

    if update_global_stats:
        curr_global_stats.num_customers_this_year = curr_global_stats.num_customers_this_year + num_customers_today
        curr_global_stats.num_dreams_this_year = curr_global_stats.num_dreams_this_year + num_dreams
        curr_global_stats.put()
        
    if num_dreams is None:
        achievement_rate = None
    else:
        achievement_rate = (num_dreams / float(daily_dream_goal)) * 100

    report = Report(
        id=date, 
        date=date_obj, 
        month_goal=month_goal,
        num_customers_today=num_customers_today,
        num_dreamers=num_dreamers,
        num_dreams=num_dreams,
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
        num_customers_this_year=num_customers_this_year,
        num_dreams_this_year=num_customers_this_year,
        year_goal=year_goal
    )
    return report


def create_report_dict_from_report_obj(curr_report):
    report_dict = {
        'year_goal': curr_report.year_goal,
        'customers_year': curr_report.num_customers_this_year if curr_report.num_customers_this_year else '',
        'dreams_year': curr_report.num_dreams_this_year if curr_report.num_dreams_this_year else '',

        'month_goal': curr_report.month_goal,
        'datestring': curr_report.date.strftime('%Y-%m-%d') if curr_report.date else '',
        'readable_datestring': curr_report.readable_datestring if curr_report.readable_datestring else '',
        'num_cust_today': curr_report.num_customers_today if curr_report.num_customers_today else '',
        'num_dreams': curr_report.num_dreams if curr_report.num_dreams else '',
        'num_dreamers': curr_report.num_dreamers if curr_report.num_dreamers else '',
        'working_members': curr_report.working_members,
        'supporting_members': curr_report.supporting_members,
        'visiting_members': curr_report.visiting_members,
        'end_time': curr_report.end_time.strftime('%H:%M') if curr_report.end_time else '',
        'pos_cycle': curr_report.positive_cycle if curr_report.positive_cycle else '',
        'total_bowls': curr_report.total_cups if curr_report.total_cups else '',
        'total_cups': curr_report.total_bowls if curr_report.total_bowls else '',
        'chopsticks_missing': curr_report.chopsticks_missing if curr_report.chopsticks_missing else '',
        'money_off_by': curr_report.money_off_by if curr_report.money_off_by else '',
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
        #curr_report = get_report_from_request(self.request, update_global_stats=False)
        curr_report_key = ndb.Key(Report, date_string)
        if date_string:
            curr_report = curr_report_key.get()
        else:
            curr_report = None
        if curr_report is not None:
            report_dict = create_report_dict_from_report_obj(curr_report)
            template_values['report'] = report_dict
        else:
            template_values['report'] = {}
        self.response.write(template.render(template_values))

    def initialize_global_stats(
            self,
            num_customers_this_year,
            num_dreams_this_year,
            daily_dream_goal,
            year_goal,
        ):
        global_stats = GlobalStats(id="global_stats",
                                    num_customers_this_year=19636,
                                    num_dreams_this_year=18000,
                                    daily_dream_goal=180,
                                    year_goal = "say less things")
        global_stats.put()

    def post(self):
        # get stuff from POST request
        # create a new Report object and save it to ndb
        new_report = get_report_from_request(self.request)
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
        # create Report object based on self.request (using the same logic as ViewReportHandler), pass it into template_values['report']
        curr_report = get_report_from_request(self.request, update_global_stats=False)

        report_dict = create_report_dict_from_report_obj(curr_report)
        template_values['report'] = report_dict
        template_values['preview'] = True
        template = JINJA_ENVIRONMENT.get_template('report.html')
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
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


app = webapp2.WSGIApplication([
    (r'/reports', ViewAllReportsHandler),
    (r'/report/(\d\d\d\d-\d\d-\d\d)', ViewReportHandler),
    (r'/createreport', CreateReportHandler),
    (r'/previewreport', PreviewReportHandler),
    (r'/', MainHandler),
], debug=True)
