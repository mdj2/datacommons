import re
import csv
import uuid
import os
from django.conf import settings as SETTINGS
from django.db import connection, transaction, DatabaseError
from .models import ColumnTypes
from .dbhelpers import sanitize

def parseCSV(filename):
    """Parse a CSV and return the header row, the data rows, inferred data
    types, and the names of the inferred data types"""
    rows = []
    max_rows = 10
    # read in the first few rows
    path = os.path.join(SETTINGS.MEDIA_ROOT, filename)
    with open(path, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        for i, row in enumerate(reader):
            if i < max_rows:
                rows.append(row)
            else:
                break

    header = [sanitize(c) for c in rows[0]]
    data = rows[1:]
    types = inferColumnTypes(data)
    type_names = [ColumnTypes.toString(type) for type in types]
    return header, data, types, type_names

def handleUploadedCSV(f):
    """Write a CSV to the media directory"""
    allowed_content_types = ['text/csv', 'application/vnd.ms-excel']
    if f.content_type not in allowed_content_types:
        raise TypeError("Not a CSV!")

    filename = uuid.uuid4()
    path = os.path.join(SETTINGS.MEDIA_ROOT, str(filename.hex) + ".csv")
    with open(path, 'wb+') as dest:
            for chunk in f.chunks():
                dest.write(chunk)
    return path

def insertCSVInto(filename, schema_name, table_name, column_names, commit=False, column_name_to_column_index=None):
    """Read a CSV and insert into schema_name.table_name"""
    # sanitize everything
    schema_name = sanitize(schema_name)
    table_name = sanitize(table_name)
    names = []
    for name in column_names:
        names.append(sanitize(name))
    column_names = names

    path = os.path.join(SETTINGS.MEDIA_ROOT, filename)
    cursor = connection.cursor()
    # build the query string
    cols = ','.join(['"' + n + '"' for n in column_names])
    escape_string = ",".join(["%s" for i in range(len(column_names))])
    sql = """INSERT INTO "%s"."%s" (%s) VALUES(%s)""" % (schema_name, table_name, cols, escape_string)
    # execute the query string for every row
    with open(path, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        for row_i, row in enumerate(reader):
            if row_i == 0: continue # skip header row
            # convert empty strings to null
            for col_i, col in enumerate(row):
                row[col_i] = col if col != "" else None

            if column_name_to_column_index is not None:
                # remap the columns
                row = [row[column_name_to_column_index[k]] for k in column_names]
            try:
                cursor.execute(sql, row)
            except DatabaseError as e:
                # give a very detailed error message
                # row_i is zero based, while the CSV is 1 based, hence the +1
                raise DatabaseError("Tried to insert line %s of the CSV, got this from database: %s. SQL was: %s" % 
                (row_i + 1, str(e), connection.queries[-1]['sql'])) 

    if commit:
        transaction.commit_unless_managed()

# helpers for parseCsv
def inferColumnType(rows, column_index):
    data = []
    for row_index in range(len(rows)):
        data.append(rows[row_index][column_index])

    # try to deduce the column type
    # is char?
    for val in data:
        # purposefully exlcuding e and E because we want to exclude numbers like 5.5e10
        if re.search(r'[A-DF-Za-df-z]', val):
            return ColumnTypes.CHAR

    # is timestamp?
    for val in data:
        if re.search(r'[:]', val):
            # if the value is longer than "2012-05-05 08:01:01" it probably
            # has a timezone appended to the end
            if len(val) > len("2012-05-05 08:01:01"):
                return ColumnTypes.TIMESTAMP_WITH_ZONE
            else:
                return ColumnTypes.TIMESTAMP

    # is numeric?
    for val in data:
        if re.search(r'[.e]', val):
            return ColumnTypes.NUMERIC

    # ...must be an int
    return ColumnTypes.INTEGER

def inferColumnTypes(rows):
    types = []
    number_of_columns = len(rows[0])
    for i in range(number_of_columns):
        types.append(inferColumnType(rows, i))
    return types
