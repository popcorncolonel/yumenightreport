from google.appengine.ext import ndb
import datetime


class Report(ndb.Model):
    '''
    Information for the daily report

    Naming convention:
    * when reporting numbers/count of things don't do num_* or count_* just say the thing
    *    if something's in the report, use that name i.e. "total bowls" -> "total_bowls"
    * always spell out the full word i.e. "customers" over "cust"
    * separate all words with underscores
    * variable name and key name need to be the same

    '''
    """ Goals snapshot """
    # snapshot
    yearly_dream_goal = ndb.IntegerProperty()
    year_goal = ndb.StringProperty()
    month_goal = ndb.StringProperty()
    daily_dream_goal = ndb.IntegerProperty()

    customers_today = ndb.IntegerProperty()
    dreams = ndb.IntegerProperty()
    dreamers = ndb.IntegerProperty()
    misc_notes = ndb.StringProperty()

    date = ndb.DateTimeProperty()
    lunch_customers_today = ndb.IntegerProperty()
    dinner_customers_today = ndb.IntegerProperty()
    lunch_dreams = ndb.IntegerProperty()
    dinner_dreams = ndb.IntegerProperty()
    lunch_dreamers = ndb.IntegerProperty()
    dinner_dreamers = ndb.IntegerProperty()

    working_members = ndb.StringProperty()
    supporting_members = ndb.StringProperty()
    visiting_members = ndb.StringProperty()
    end_time = ndb.TimeProperty()
    total_bowls = ndb.IntegerProperty()
    total_cups = ndb.IntegerProperty()
    chopsticks_missing = ndb.IntegerProperty()
    money_off_by = ndb.IntegerProperty()
    positive_cycle = ndb.IntegerProperty()

    # hack for optimization. computes all stats based on the specificed list of Reports, but
    # needs to be passed in beforehand. probably don't put() a Report with this attribute
    # set, who knows what'll happen
    report_list = None

    def get_previous_reports(self):
        ''' Get all reports with dates less than the date of this report (in the same year), as well as this report '''
        if self.date is None:
            date = (datetime.datetime.now() - datetime.timedelta(hours=12)).date()
        else:
            date = self.date.date()
        older_reports = [report for report in self.get_reports_for_year(date) if report.date.date() < date]
        if self.is_finalized():
            older_reports.append(self)
        previous_reports = older_reports
        return sorted(previous_reports, key=lambda x: x.date)

    def get_perfect_money_marathon(self):
        marathon = 0
        # Go most recent to least recent
        for report in reversed(self.get_previous_reports()):
            if report.money_off_by == 0:
                marathon += 1
            else:
                break
        return marathon

    def get_dreams_this_year(self):
        return sum(report.get_dreams() for report in self.get_previous_reports())


    def get_dreamers_this_year(self):
        return sum(report.get_dreamers() for report in self.get_previous_reports())

    def get_customers_this_year(self):
        return sum(report.get_customers_today() for report in self.get_previous_reports())

    def is_finalized(self):
        ''' Returns True if all appropriate fields are populated. '''
        return (self.get_dreams() is not None and
                self.get_customers_today() is not None and
                self.get_dreamers() is not None)

    def get_achievement_rate(self):
        daily_dream_goal = self.get_daily_dream_goal()
        if self.dreams is None:
            return None
        else:
            if daily_dream_goal == 0:
                return 100.
        achievement_rate = (self.dreams / float(daily_dream_goal)) * 100
        return achievement_rate

    def get_daily_dream_goal(self):
        from main import get_working_days_left_in_year
        if self.date is None:
            date = (datetime.datetime.now() - datetime.timedelta(hours=12)).date()
        else:
            date = self.date.date()
        working_days_left_in_year = get_working_days_left_in_year(date)
        if working_days_left_in_year == 0:
            return 1
        total_dreams_for_year = self.get_dreams_for_year2(date)
        dreams_remaining = max(0, self.yearly_dream_goal - total_dreams_for_year)
        return int(dreams_remaining / float(working_days_left_in_year))

    def get_customers_today(self):
        if self.lunch_customers_today is None or self.dinner_customers_today is None:
            return None
        return self.lunch_customers_today + self.dinner_customers_today

    def get_dreamers(self):
        if self.lunch_dreamers is None or self.dinner_dreamers is None:
            return None
        return self.lunch_dreamers + self.dinner_dreamers

    def get_dreams(self):
        if self.lunch_dreams is None or self.dinner_dreams is None:
            return None
        return self.lunch_dreams + self.dinner_dreams

    @staticmethod
    def get_all_reports():
        return Report.query().order(-Report.date).fetch()

    def get_reports_for_year2(self, datetime_obj):
        ''' Gets all reports logged in the year of `datetime_obj` '''
        if self.report_list is not None:
            all_reports = self.report_list
        else:
            all_reports = Report.get_all_reports()
        return [x for x in all_reports if x.date.date().year == datetime_obj.year and x.is_finalized()]

    def get_dreams_for_year2(self, datetime_obj):
        return sum(report.get_dreams() for report in self.get_reports_for_year2(datetime_obj))

    def get_dreamers_for_year2(self, datetime_obj):
        return sum(report.get_dreamers() for report in self.get_reports_for_year2(datetime_obj))

    def get_customers_for_year2(self, datetime_obj):
        return sum(report.get_customers_today() for report in self.get_reports_for_year2(datetime_obj))

    @staticmethod
    def get_reports_for_year(datetime_obj, report_list=None):
        ''' Gets all reports logged in the year of `datetime_obj` '''
        if report_list is not None:
            all_reports = report_list
        else:
            all_reports = Report.get_all_reports()
        return [x for x in all_reports if x.date.date().year == datetime_obj.year and x.is_finalized()]

    @staticmethod
    def get_dreams_for_year(datetime_obj, report_list=None):
        return sum(report.get_dreams() for report in Report.get_reports_for_year(datetime_obj, report_list))

    @staticmethod
    def get_dreamers_for_year(datetime_obj, report_list=None):
        return sum(report.get_dreamers() for report in Report.get_reports_for_year(datetime_obj, report_list))

    @staticmethod
    def get_customers_for_year(datetime_obj, report_list=None):
        return sum(report.get_customers_today() for report in Report.get_reports_for_year(datetime_obj, report_list))

    @property
    def date_string(self):
        ''' 2018-06-13 '''
        if self.date:
            return self.date.strftime('%Y-%m-%d')
        else:
            return None

    @property
    def readable_date_string(self):
        ''' Tuesday June 13, 2018 '''
        if self.date:
            return self.date.strftime('%A %B %d, %Y')
        else:
            return None

    def update(self, old_report):
        '''
        StringProperties are not checked for None because they can be "" which we don't want (and it's also not None)
        '''
        if old_report.year_goal: self.year_goal = old_report.year_goal
        if old_report.month_goal: self.month_goal = old_report.month_goal
        if old_report.working_members: self.working_members = old_report.working_members
        if old_report.supporting_members: self.supporting_members = old_report.supporting_members
        if old_report.visiting_members: self.visiting_members = old_report.visiting_members
        if old_report.misc_notes: self.misc_notes = old_report.misc_notes

        if old_report.yearly_dream_goal is not None: self.yearly_dream_goal = old_report.yearly_dream_goal
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
        if old_report.end_time is not None: self.end_time = old_report.end_time
        if old_report.total_bowls is not None: self.total_bowls = old_report.total_bowls
        if old_report.total_cups is not None: self.total_cups = old_report.total_cups
        if old_report.chopsticks_missing is not None: self.chopsticks_missing = old_report.chopsticks_missing
        if old_report.money_off_by is not None: self.money_off_by = old_report.money_off_by
        if old_report.positive_cycle is not None: self.positive_cycle = old_report.positive_cycle

