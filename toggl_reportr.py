#!/usr/bin/python

import sys
import csv
import requests
import argparse
import datetime
import ConfigParser


class Reporter(object):
    def __init__(self):
        self.reports_api = 'https://toggl.com/reports/api/v2/details.csv'
        self.tracking_api = 'https://toggl.com/api/v8/'

        config = ConfigParser.ConfigParser()
        config.read('.togglrc')

        self.api_token = config.get('toggl', 'apikey')
        self.workspace = config.get('toggl', 'workspace')
        self.api_auth = requests.auth.HTTPBasicAuth(self.api_token, 'api_token')
        self.default_params = {
            'rounding': 'Off',
            'status': 'active',
            'billable': 'both',
            'calculate': 'time',
            'sortDirection': 'asc',
            'sortBy': 'date',
            'page': '1',
            'with_total_currencies': '1',
            'subgrouping': 'time_entries',
            'order_field': 'date',
            'order_desc': 'off',
            'distinct_rates': 'Off',
            'bars_count': '31',
            'subgrouping_ids': 'true',
            'date_format': 'MM%2FDD%2FYYYY',
            'user_agent': 'toggl-reportr ryan@krabath.net',
        }


    def get_report_data(self, endpoint, extra_params=None):
        url = "{0}{1}".format(self.reports_api, endpoint)
        params = self.default_params
        params.update(extra_params)
        params['workspace_id'] = self.workspace
        response = requests.get(url, params=params, auth=self.api_auth, stream=True)
        if response.status_code != 200:
            raise ValueError("Status code indicates error: " + str(response.status_code) + "\n" + response.text)
        response.raw.read(3) # Clear the phantom \xef\xbb\xbf 
        reader = csv.DictReader(response.raw)
        return reader


    def get_tracker_data(self, endpoint, terms):
        url = "{0}{1}".format(self.tracker_api, endpoint)
        params = self.default_params
        params.update(extra_params)
        response = requests.get(url, params=params, auth=self.api_auth)
        if response.status_code != 200:
            raise ValueError("Status code indicates error: " + int(response.status_code) + "\n" + response.text)
        return response.json()


    def tags_report(self, params):
        #TODO: Make this not ugly
        # Initialize 
        return_value = ""
        total_time = duration_to_timedelta('00:00:00')
        report = {}
        for tag in params['tags']:
            report[tag] = duration_to_timedelta('00:00:00')

        # Get data
        data = self.get_report_data('details.csv', params)
        for line in data:
            time = duration_to_timedelta(line['Duration'])
            total_time += time
            entry_tags = [x.strip().lower() for x in line['Tags'].split(',')]
            for tag in params['tags']:
                if tag.lower() in entry_tags:
                    report[tag] += time

        #TODO: Seperate processing and output into seperate sections
        total_tagged_time = sum(report.values(), duration_to_timedelta('00:00:00'))
        report['other'] = total_time - total_tagged_time #TODO: OrderedDict
        for tag in report:
            duration = report[tag]
            try:
                percent = duration.total_seconds()/total_time.total_seconds() * 100
            except ZeroDivisionError:
                percent = 0.0
            return_value += "{tag:10}  {duration:>9} ({percent:.2f}%)\n".format(tag=tag+':', duration=duration, percent=percent)
            #TODO: Total

        return return_value


    def user_list(self, params):
        return_value = ""
        users = self.get_tracker_data('workspaces/{0}/users'.format(self.workspace))
        for user in users:
            return_value += "{0:10}  {1}\n".format(user['id'], user['email'])
        return return_value


def duration_to_timedelta(duration):
    h, m, s = duration.split(':')
    return datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(s) )


def main():

    #TODO: Parse comma seperated lists instead of supplying argument repeatidly
    parser = argparse.ArgumentParser(description='Reports from Toggl')
    parser.add_argument('-u', '--user', action='append')
    parser.add_argument('--list-users', action='store_true')
    parser.add_argument('--report', action='store_true')
    parser.add_argument('-t', '--tag', action='append')
    parser.add_argument('-s', '--span')

    args = parser.parse_args()
    reporter = Reporter()

    params = {}

    if args.user:
        params['user_ids'] = args.user

    if args.span:
        params['since'] = datetime.date.today() - datetime.timedelta(days=int(args.span))
    else:
        params['since'] = datetime.date.today()

    if args.tag:
        params['tags'] = args.tag
    

    if args.report:
        print reporter.tags_report(params)

    if args.list_users:
        print reporter.user_list(params)

    #TODO: report 3: Project breakout

    #TODO: report 4: User breakout

if __name__ == "__main__":
    main()
    

