import webapp2
import jinja2
import os

from google.appengine.ext import ndb


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

    num_customers = ndb.IntegerProperty()
    num_dreamers = ndb.IntegerProperty()
    num_dreams = ndb.IntegerProperty()
    end_time = ndb.IntegerProperty()
    total_bowls = ndb.IntegerProperty()
    total_cups = ndb.IntegerProperty()
    chopsticks_missing = ndb.IntegerProperty()
    money_off_by = ndb.IntegerProperty()
    positive_cycle = ndb.IntegerProperty()

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
        pass


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
    (r'/', MainHandler),
], debug=True)
