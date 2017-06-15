import webapp2
import jinja2
import os

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
            return self.date.strftime('%Y-%M-%D')
        else:
            return None

    @property
    def readable_datestring(self):
        ''' Tuesday June 13, 2017 '''
        if self.date:
            return self.date.strftime('%A %b %-d, %Y')
        else:
            return None


class ViewAllReportsHandler(webapp2.RequestHandler):
    '''
    Handler to view a list of all the existing daily reports
    '''
    def get(self):
        template_values = {}
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
        template = JINJA_ENVIRONMENT.get_template('report.html')
        """  #  FOR TESTING
        report = {
            'readable_datestring': 'Tuesday June 13, 2017',
            'yeargoal': 'Dont say a lot of things',
            'monthgoal': '???',
            'customers_today': 69,
            'customers_year': 420,
            'dreams_today': 50,
            'dreams_year': 50000,
            'dreamers_today': 20,
            'dreamers_year': 300,
            'working_members': ['jake', 'dan', 'naomi'],
            'supporting_members': ['makoto'],
            'visiting_members': ['eric'],
            'endtime': '11:15',
            'positivecycle': 60,
            'totalbowls': 50,
            'totalcups': 40,
            'chopsticks_missing': 30,
            'money_off_by': 20,
        }
        template_values['report'] = report
        """
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

    def post(self):
        # get stuff from POST request
        # create a new Report object and save it to ndb
        date = self.request.get('date')
        month_goal = self.request.get('month_goal')
        num_customers_today = int(self.request.get('num_cust_today'))
        num_dreamers = int(self.request.get('num_dreamers'))
        num_dreams = int(self.request.get('num_dreams'))
        
        # calculate this
        # add to total number of dreams this year
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
        end_time_obj = datetime.strptime(end_time, '%H:%M').time()
        key = ndb.Key(GlobalStats, "global_stats")
        curr_global_stats = key.get()
        curr_global_stats.num_customers_this_year = curr_global_stats.num_customers_this_year +  num_customers_today
        curr_global_stats.num_dreams_this_year = curr_global_stats.num_dreams_this_year + num_dreams
        curr_global_stats.put()
        achievement_rate = (num_dreams/float(curr_global_stats.daily_dream_goal)) * 100

        new_report = Report(date=date_obj,
                            id=date, 
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
                            achievement_rate=achievement_rate)
        new_report.put()


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
