import json
from flask import Response

def raiseException(exception):
    if exception.__class__.__name__ == "IntegrityError":
        return Response(json.dumps({
                "Error": "Duplicate Entry!",
                "Type": str(exception.__class__.__name__)
            }), status=400)
    status = 500
    if exception.__class__ == AssertionError:
        status = 400
    return Response(json.dumps({
        "Error": str(exception),
        "Type": str(exception.__class__.__name__)
        }), status=status)