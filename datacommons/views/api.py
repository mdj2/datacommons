import decimal
import os
import re
import json
from datacommons.unicodecsv import UnicodeWriter
from django.conf import settings as SETTINGS
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.db import DatabaseError
from django.core.exceptions import PermissionDenied
from ..models.dbhelpers import fetchRowsFor

def view(request, schema, table, format):
    """View the table in schema, including the column names and types"""
    # get all the data
    rows, cols = fetchRowsFor(schema, table)

    response = HttpResponse()
    if format == "csv":
        response['Content-Type'] = 'text/csv'
        writer = UnicodeWriter(response)
        writer.writerow([t.name for t in cols])
        for row in rows:
            writer.writerow([unicode(c) for c in row])
    elif format == "json":
        response['Content-Type'] = 'application/json'
        data = []
        for row in rows:
            data.append(dict([(col.name, cell) for col, cell in zip(cols, row)]))
        json.dump(data, response, cls=JSONEncoder)

    return response 

# since Python's default JSONEncoder doesn't handle decimal types, we have to
# add support for that on our own
class JSONEncoder(json.JSONEncoder):
    def _iterencode(self, o, *args, **kwargs):
        if isinstance(o, decimal.Decimal):
            return (str(o),)
        return super(JSONEncoder, self)._iterencode(o, *args, **kwargs)
