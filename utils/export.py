"""CSV downloads."""
import csv
import io
import json

from flask import Response


def _cell(value):
    if value is None:
        return ''
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def csv_response(columns, rows, filename: str) -> Response:
    """A CSV attachment. Cells with commas, quotes or newlines are quoted, lists and
    dicts are written as JSON, and None is an empty cell."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\n')
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_cell(value) for value in row])
    return Response(buffer.getvalue(), mimetype='text/csv',
                    headers={"Content-Disposition": f"attachment;filename={filename}"})
