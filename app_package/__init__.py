from flask import Flask
from ._common.config import config
from ._common.utilities import login_manager, custom_logger_init, \
    before_request_custom, teardown_request
import os
from pytz import timezone
from datetime import datetime
from flask_mail import Mail
from ws_models import Base, engine

if not os.path.exists(os.path.join(os.environ.get('API_ROOT'),'logs')):
    os.makedirs(os.path.join(os.environ.get('API_ROOT'), 'logs'))

logger_init = custom_logger_init()

logger_init.info(f'--- Starting WhatSticks13 API ---')
logger_init.info(f'ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT: {config.ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT}')

mail = Mail()

def create_app(config_for_flask = config):
    logger_init.info("- WhatSticks13Api/app_package/__init__.py create_app() -")
    app = Flask(__name__)
    # app.teardown_appcontext(teardown_appcontext)
    app.before_request(before_request_custom)
    app.teardown_request(teardown_request)
    app.config.from_object(config_for_flask)
    mail.init_app(app)

    ############################################################################
    ## create folders for PROJECT_RESOURCES
    create_folder(config_for_flask.PROJECT_RESOURCES)
    create_folder(config_for_flask.DIR_LOGS)
    create_folder(os.path.join(config_for_flask.API_ROOT,"logs"))
    # database helper files
    create_folder(config_for_flask.DATABASE_HELPER_FILES)
    create_folder(config_for_flask.APPLE_HEALTH_DIR)
    create_folder(config_for_flask.DATAFRAME_FILES_DIR)
    create_folder(config_for_flask.USER_LOCATION_JSON)
    # ios helper files
    create_folder(config_for_flask.WS_IOS_HELPER_FILES)
    create_folder(config_for_flask.DASHBOARD_FILES_DIR)
    create_folder(config_for_flask.DATA_SOURCE_FILES_DIR)
    # user files
    create_folder(config_for_flask.USER_FILES)
    create_folder(config_for_flask.DAILY_CSV)
    create_folder(config_for_flask.RAW_FILES_FOR_DAILY_CSV)
    ############################################################################
    # Build MySQL database
    # Base.metadata.create_all(engine)
    logger_init.info(f"- MYSQL_USER: {config_for_flask.MYSQL_USER}")
    logger_init.info(f"- MYSQL_DATABASE_NAME: {config_for_flask.MYSQL_DATABASE_NAME}")

    from app_package.bp_users.routes import bp_users
    from app_package.bp_apple_health.routes import bp_apple_health
    from app_package.bp_errors.routes import bp_errors

    app.register_blueprint(bp_users)
    app.register_blueprint(bp_apple_health)
    app.register_blueprint(bp_errors)

    return app

def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logger_init.info(f"created: {folder_path}")
