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

        stats_key = ndb.Key(GlobalStats, "global_stats")
        curr_global_stats = stats_key.get()

        report = {
            'year_goal': curr_global_stats.year_goal,
            'customers_year': curr_global_stats.num_customers_this_year,
            'dreams_year': curr_global_stats.num_dreams_this_year,

            'month_goal': curr_report.month_goal,
            'readable_datestring': curr_report.readable_datestring,
            'num_cust_today': curr_report.num_customers_today,
            'num_dreams': curr_report.num_dreams,
            'num_dreamers': curr_report.num_dreamers,
            'working_members': curr_report.working_members,
            'supporting_members': curr_report.supporting_members,
            'visiting_members': curr_report.visiting_members,
            'end_time': curr_report.end_time.strftime('%H:%Mpm'),
            'pos_cycle': curr_report.positive_cycle,
            'total_bowls': curr_report.total_cups,
            'total_cups': curr_report.total_bowls,
            'chopsticks_missing': curr_report.chopsticks_missing,
            'money_off_by': curr_report.money_off_by,
        }
        template_values['report'] = report
        today_datetime = datetime.now()
        template_values['today_datestring'] = today_datetime.strftime('%Y-%m-%d')
        
        template = JINJA_ENVIRONMENT.get_template('report.html')
        self.response.write(template.render(template_values))


class CreateReportHandler(webapp2.RequestHandler):
    '''
    Handler to create a new report.
        GET this endpoint to get a create report form
        POST here to save a new one do the db
    '''
    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('createreport.html')
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
        date = self.request.get('date')
        month_goal = self.request.get('month_goal')
        num_customers_today = int(self.request.get('num_cust_today'))
        num_dreamers = int(self.request.get('num_dreamers'))
        num_dreams = int(self.request.get('num_dreams'))
        working_members = self.request.get('working_members')
        supporting_members = self.request.get('supporting_members')
        visiting_members = self.request.get('visiting_members')
        end_time = self.request.get('end_time')
        total_bowls = int(self.request.get('total_bowls'))
        total_cups = int(self.request.get('total_cups'))
        chopsticks_missing = int(self.request.get('chopsticks_missing'))
        money_off_by = int(self.request.get('money_off_by'))
        positive_cycle = int(self.request.get('pos_cycle'))
        
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        if ':' in end_time:
            end_time_obj = datetime.strptime(end_time, '%H:%M').time()  # deal w/ am/pm?
        else:
            end_time_obj = datetime.strptime(end_time, '%H%M').time()  # deal w/ am/pm?

        global_stats_key = ndb.Key(GlobalStats, "global_stats")
        curr_global_stats = global_stats_key.get()

        old_report_key = ndb.Key(Report, date)
        old_report = old_report_key.get()
        if old_report is None:
            curr_global_stats.num_customers_this_year = curr_global_stats.num_customers_this_year + num_customers_today
            curr_global_stats.num_dreams_this_year = curr_global_stats.num_dreams_this_year + num_dreams
            curr_global_stats.put()
        else:
            raise endpoints.BadRequestException("Report already exists for {} (TODO: allow for re-uploading of dates)".format(date))
            
        achievement_rate = (num_dreams / float(curr_global_stats.daily_dream_goal)) * 100

        new_report = Report(
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
        )
        new_report.put()
        report_page = '/report/' + date
        self.redirect(report_page)


class PreviewReportHandler(webapp2.RequestHandler):
    '''
    Handler to preview a report.
        GET this endpoint to get a create report form
        POST here to save a new one do the db
    '''
    def get(self):
        template_values = {}
        # TODO: create Report object based on self.request (using the same logic as ViewReportHandler), pass it into template_values['report']
        template_values['report'] = None
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
