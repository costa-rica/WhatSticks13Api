from flask import Blueprint, jsonify, g
import werkzeug.exceptions
from app_package._common.utilities import custom_logger, wrap_up_session

# Assuming the logger name is a typo and fixing it.
logger_bp_errors = custom_logger('bp_errors.log')
bp_errors = Blueprint('bp_errors', __name__)


# @bp_errors.after_request
# def after_request(response):
#     logger_bp_errors.info(f"---- after_request --- ")
#     if hasattr(g, 'db_session'):
#         wrap_up_session(logger_bp_errors, g.db_session)
#     return response

@bp_errors.app_errorhandler(Exception)
def handle_exception(e):
    logger_bp_errors.info(f"--- in def handle_exception(e) ---")
    # Attempt to retrieve the db_session from g, if it has been set
    db_session = getattr(g, 'db_session', None)
    
    # If db_session exists, log its ID
    if db_session:
        session_id = id(db_session)
        logger_bp_errors.info(f"Session ID: {session_id} - Error during exception handling: {type(e).__name__}: {e}")
        # Including the stack trace in the log
        logger_bp_errors.error(f"Exception stack trace:", exc_info=True)
    else:
        # Log the error normally if db_session is not found
        logger_bp_errors.error(f'Unhandled Exception: {type(e).__name__}: {e}', exc_info=True)

    # You can check if the error is an HTTPException and use its code
    # Otherwise, use 500 by default for unknown exceptions
    if isinstance(e, werkzeug.exceptions.HTTPException):
        error_code = e.code
    else:
        error_code = 500
    error_type = type(e).__name__

    response_dict = {
        'alert_title': "Error",
        'alert_message': f"Error Type: {error_type}, Error Code: {error_code}"
    }

    # Use the correct logger
    logger_bp_errors.info(f"- response_dict: {response_dict} -")
    return jsonify(response_dict), error_code

