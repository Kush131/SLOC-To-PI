#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=import-error
"""JIRA Query"""
import logging
import api
import requests

requests.packages.urllib3.disable_warnings()

LOGGER = logging.getLogger(__name__)


def query(jql, fields=None):
    """Return list of JIRA Query results

    Args:
        jql(string): JIRA Query to execute
        fields(list): List of fields to retrieve
    """
    start_at = 0
    result = {}
    ret_val = []

    if fields is None:
        fields = ['*all']

    LOGGER.info('Retrieving Query Results')
    LOGGER.debug('jql:%s fields:%s', jql, ','.join(fields))

    # Compile results while adhering to MaxResult size
    # limitations imposed by JIRA

    while start_at == 0 or start_at <= result['total']:
        LOGGER.info('  Retrieved %i Issues', start_at)
        payload = {'jql': jql,
                   'startAt': start_at,
                   'fields': fields,
                   'maxResults': 10000}

        print(payload)
        result = api.BASE.search.post(payload)

        ret_val += result['issues']
        start_at += result['maxResults']

    LOGGER.info('Query Completed(%i Issues Retrieved)', result['total'])

    return ret_val
