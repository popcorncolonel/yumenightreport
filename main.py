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
    customers_this_year = ndb.IntegerProperty()
    dreams_this_year = ndb.IntegerProperty()
    daily_dream_goal = ndb.IntegerProperty()  # how many dreams would we like today?
    year_goal = ndb.StringProperty()


class Report(ndb.Model):
    '''
    Information for the daily report
    '''
    date = ndb.DateTimeProperty()
    month_goal = ndb.StringProperty()
    customers_today = ndb.IntegerProperty()
    dreamers = ndb.IntegerProperty()
    dreams = ndb.IntegerProperty()
       
    """ Global stats snapshot """
    year_goal = ndb.StringProperty()
    customers_this_year = ndb.IntegerProperty()
    dreams_this_year = ndb.IntegerProperty()
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

    misc_notes = ndb.StringProperty()

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
    def get(self, datestring):
        '''
        Get corresponding report from datestring, if it exists. if not, 404
        We should allow editing of a report, which takes you to CreateReportHandler with all the info already pre-filled in
        '''
        template_values = {}

        report_key = ndb.Key(Report, datestring)
        current_report = report_key.get()
        if current_report is None:
            raise endpoints.NotFoundException("No report found for {}".format(datestring))

        report_dict = create_report_dict_from_report_obj(current_report)

        template_values['report'] = report_dict
        today_datetime = datetime.now()
        template_values['today_datestring'] = today_datetime.strftime('%Y-%m-%d')
        template_values['hidetitleimg'] = True
        
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
    '''
    Naming convention: 
    * when reporting numbers/count of things don't do num_* or count_* just say the thing
    *    if something's in the report, use that name i.e. "total bowls" -> "total_bowls"
    * always spell out the full word i.e. "customers" over "cust"
    * separate all words with underscores
    * variable name and key name need to be the same
    '''
    date = request.get('date', '')
    month_goal = request.get('month_goal', '')
    customers_today = get_integer_input(request, 'customers_today')
    dreamers = get_integer_input(request, 'dreamers')
    dreams = get_integer_input(request, 'dreams')
    working_members = request.get('working_members', '')
    supporting_members = request.get('supporting_members', '')
    visiting_members = request.get('visiting_members', '')
    end_time = request.get('end_time', '')
    total_bowls = get_integer_input(request, 'total_bowls')
    total_cups = get_integer_input(request, 'total_cups')
    chopsticks_missing = get_integer_input(request,'chopsticks_missing')
    money_off_by = get_integer_input(request, 'money_off_by')
    positive_cycle = get_integer_input(request, 'positive_cycle')
    misc_notes = request.get('misc_notes', '')
    
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
    current_global_stats = global_stats_key.get()

    if date != '':
        old_report_key = ndb.Key(Report, date)
        old_report = old_report_key.get()
    else:
        old_report = None
    year_goal = current_global_stats.year_goal
    if old_report is None:
        #current_global_stats.dreams_this_year = 1000
        #current_global_stats.customers_this_year = 1000
        #current_global_stats.daily_dream_goal = 100
        #current_global_stats.put()
        daily_dream_goal = current_global_stats.daily_dream_goal
        dreams_this_year = current_global_stats.dreams_this_year
        customers_this_year = current_global_stats.customers_this_year
    else:
        if update_global_stats:
            current_global_stats.customers_this_year = current_global_stats.customers_this_year - old_report.customers_today
            current_global_stats.dreams_this_year = current_global_stats.dreams_this_year - old_report.dreams
        daily_dream_goal = old_report.daily_dream_goal or 100
        dreams_this_year = old_report.dreams_this_year + (dreams - old_report.dreams)
        customers_this_year = old_report.customers_this_year  + (customers_today - old_report.customers_today) 

    if update_global_stats:
        current_global_stats.customers_this_year = current_global_stats.customers_this_year + customers_today
        current_global_stats.dreams_this_year = current_global_stats.dreams_this_year + dreams
        current_global_stats.put()
        
    if dreams is None:
        achievement_rate = None
    else:
        achievement_rate = (dreams / float(daily_dream_goal)) * 100

    report = Report(
        id=date, 
        date=date_obj, 
        month_goal=month_goal,
        customers_today=customers_today,
        dreamers=dreamers,
        dreams=dreams,
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
        customers_this_year=customers_this_year,
        dreams_this_year=customers_this_year,
        year_goal=year_goal,
        misc_notes=misc_notes,
    )
    return report


def create_report_dict_from_report_obj(current_report):
    report_dict = {
        'year_goal': current_report.year_goal,
        'customers_year': current_report.customers_this_year if current_report.customers_this_year else '',
        'dreams_year': current_report.dreams_this_year if current_report.dreams_this_year else '',

        'month_goal': current_report.month_goal,
        'date': current_report.date.strftime('%Y-%m-%d') if current_report.date else '',
        'datestring': current_report.date.strftime('%Y-%m-%d') if current_report.date else '',
        'readable_datestring': current_report.readable_datestring if current_report.readable_datestring else '',
        'customers_today': current_report.customers_today if current_report.customers_today else '',
        'dreams': current_report.dreams if current_report.dreams else '',
        'dreamers': current_report.dreamers if current_report.dreamers else '',
        'working_members': current_report.working_members,
        'supporting_members': current_report.supporting_members,
        'visiting_members': current_report.visiting_members,
        'end_time': current_report.end_time.strftime('%H:%M') if current_report.end_time else '',
        'positive_cycle': current_report.positive_cycle if current_report.positive_cycle else '',
        'total_bowls': current_report.total_cups if current_report.total_cups else '',
        'total_cups': current_report.total_bowls if current_report.total_bowls else '',
        'chopsticks_missing': current_report.chopsticks_missing if current_report.chopsticks_missing else '',
        'money_off_by': current_report.money_off_by if current_report.money_off_by else '',
        'misc_notes': current_report.misc_notes,
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
        #current_report = get_report_from_request(self.request, update_global_stats=False)
        current_report_key = ndb.Key(Report, date_string)
        if date_string:
            current_report = current_report_key.get()
        else:
            current_report = None
        if current_report is not None:
            report_dict = create_report_dict_from_report_obj(current_report)
            template_values['report'] = report_dict
        else:
            template_values['report'] = {}
        template_values['hidetitleimg'] = True
        self.response.write(template.render(template_values))

    def initialize_global_stats(
            self,
            customers_this_year,
            dreams_this_year,
            daily_dream_goal,
            year_goal,
        ):
        global_stats = GlobalStats(id="global_stats",
                                    customers_this_year=19636,
                                    dreams_this_year=18000,
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
        current_report = get_report_from_request(self.request, update_global_stats=False)

        report_dict = create_report_dict_from_report_obj(current_report)
        template_values['report'] = report_dict
        template_values['preview'] = True
        template_values['hidetitleimg'] = True
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
    (r'/', ViewAllReportsHandler),
], debug=True)
