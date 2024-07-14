from flask import current_app, url_for
import json
from ws_models import DatabaseSession, Users, Locations
from flask_mail import Message
from app_package import mail
import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
import pandas as pd
import requests
from datetime import datetime 
from ws_models import DatabaseSession, Users, AppleHealthQuantityCategory, \
    AppleHealthWorkout, UserLocationDay, Locations
from app_package._common.utilities import custom_logger, wrap_up_session
from itsdangerous.url_safe import URLSafeTimedSerializer#new 2023
from sqlalchemy import desc

logger_bp_users = custom_logger('bp_users.log')


def send_reset_email(user):
    token = user.get_reset_token()
    logger_bp_users.info(f"current_app.config.get(MAIL_USERNAME): {current_app.config.get('MAIL_USERNAME')}")
    msg = Message('Password Reset Request',
                  sender=current_app.config.get('MAIL_USERNAME'),
                  recipients=[user.email])
    
    # Replace 'url_for' with the full external reset URL, appending the token as a query parameter
    base_url = website_url()
    reset_url = f"{base_url}/reset_password?token={token}"
    
    long_f_string = (
        "To reset your password, visit the following link:" +
        f"\n {reset_url} " +
        "\n\n" +
        "If you did not make this request, simply ignore this email and no changes will be made."
    )
    msg.body =long_f_string

    mail.send(msg)

def send_confirm_email(email):
    if os.environ.get('WS_CONFIG_TYPE') != 'workstation':
        logger_bp_users.info(f"-- sending email to {email} --")
        msg = Message('Welcome to What Sticks!',
            sender=current_app.config.get('MAIL_USERNAME'),
            recipients=[email])
        msg.body = 'You have succesfully been registered to What Sticks.'
        mail.send(msg)
        logger_bp_users.info(f"-- email sent --")
    else :
        logger_bp_users.info(f"-- Non prod mode so no email sent --")


def delete_user_data_files(current_user):
    
    # dataframe pickle - apple category & quantity
    user_apple_health_dataframe_pickle_file_name = f"user_{current_user.id:04}_apple_health_dataframe.pkl"
    pickle_data_path_and_name = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_health_dataframe_pickle_file_name)
    if os.path.exists(pickle_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_apple_health_dataframe_pickle_file_name} successfully -")
        os.remove(pickle_data_path_and_name)
    
    # dataframe pickle - apple workouts
    user_apple_health_workouts_dataframe_pickle_file_name = f"user_{current_user.id:04}_apple_workouts_dataframe.pkl"
    pickle_data_path_and_name = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_health_workouts_dataframe_pickle_file_name)
    if os.path.exists(pickle_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_apple_health_workouts_dataframe_pickle_file_name} successfully -")
        os.remove(pickle_data_path_and_name)

    # data source json
    user_data_source_json_file_name = f"data_source_list_for_user_{current_user.id:04}.json"
    json_data_path_and_name = os.path.join(current_app.config.get('DATA_SOURCE_FILES_DIR'), user_data_source_json_file_name)
    if os.path.exists(json_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_data_source_json_file_name} successfully -")
        os.remove(json_data_path_and_name)

    # dashboard json
    # user_sleep_dash_json_file_name = f"dt_sleep01_{current_user.id:04}.json"
    user_sleep_dash_json_file_name = f"data_table_objects_array_{current_user.id:04}.json"
    json_data_path_and_name = os.path.join(current_app.config.get('DASHBOARD_FILES_DIR'), user_sleep_dash_json_file_name)
    if os.path.exists(json_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_sleep_dash_json_file_name} successfully -")
        os.remove(json_data_path_and_name)


def delete_user_daily_csv(current_user):
    # user_files/daily_csv/
    # format: user_0001_df_daily_sleep_heart_rate.csv
    if os.path.exists(current_app.config.get('DAILY_CSV')):
        for filename in os.listdir(current_app.config.get('DAILY_CSV')):
            if f"user_{current_user.id:04}_df" in filename:
                os.remove(os.path.join(current_app.config.get('DAILY_CSV'), filename))


def delete_user_from_table(current_user, table):
    db_session = DatabaseSession()
    count_deleted_rows = 0
    error = None
    try:
        if table.__tablename__ != "users":
            count_deleted_rows = db_session.query(table).filter_by(user_id = current_user.id).delete()
        else:
            count_deleted_rows = db_session.query(table).filter_by(id = current_user.id).delete()
        wrap_up_session(logger_bp_users, db_session)
        response_message = f"Successfully deleted {count_deleted_rows} records from {table.__tablename__}"
    except Exception as e:
        db_session.rollback()
        error_message = f"Failed to delete data from {table.__tablename__}, error: {e}"
        logger_bp_users.info(error_message)
        error = e
    
    return count_deleted_rows, error


def get_apple_health_count_date(user_id):
    user_apple_qty_cat_dataframe_pickle_file_name = f"user_{int(user_id):04}_apple_health_dataframe.pkl"
    user_apple_workouts_dataframe_pickle_file_name = f"user_{int(user_id):04}_apple_workouts_dataframe.pkl"
    pickle_data_path_and_name_qty_cat = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_qty_cat_dataframe_pickle_file_name)
    pickle_data_path_and_name_workouts = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_workouts_dataframe_pickle_file_name)
    df_apple_qty_cat = pd.read_pickle(pickle_data_path_and_name_qty_cat)
    df_apple_workouts = pd.read_pickle(pickle_data_path_and_name_workouts)

    # get count of qty_cat and workouts
    apple_health_record_count = "{:,}".format(len(df_apple_qty_cat) + len(df_apple_workouts))

    # Convert startDate to datetime
    df_apple_qty_cat['startDate'] = pd.to_datetime(df_apple_qty_cat['startDate'])
    earliest_date_qty_cat = df_apple_qty_cat['startDate'].min()

    df_apple_workouts['startDate'] = pd.to_datetime(df_apple_workouts['startDate'])
    earliest_date_workouts = df_apple_workouts['startDate'].min()
    earliest_date_str = ""
    if earliest_date_workouts < earliest_date_qty_cat:
        # formatted_date_workouts = earliest_date_workouts.strftime('%b %d, %Y')
        # print(f"workouts are older: {formatted_date_workouts}")
        earliest_date_str = earliest_date_workouts.strftime('%b %d, %Y')
    else:
        # formatted_date_qty_cat = earliest_date_qty_cat.strftime('%b %d, %Y')
        # print(f"qty_cat are older: {formatted_date_qty_cat}")
        earliest_date_str = earliest_date_qty_cat.strftime('%b %d, %Y')

    return apple_health_record_count, earliest_date_str

def website_url():
    match os.environ.get('WS_CONFIG_TYPE'):
        case 'dev':
            base_url = f"https://dev.what-sticks.com"
        case 'prod':
            base_url = f"https://what-sticks.com"
        case _:
            base_url = f"http://localhost:5000"
    
    return base_url

def create_user_obj_for_swift_login(user, db_session):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    user_object_for_swift_app = {}
    user_object_for_swift_app['id'] = str(user.id)
    user_object_for_swift_app['email'] = user.email
    user_object_for_swift_app['username'] = user.username
    user_object_for_swift_app['admin_permission'] = user.admin_permission
    # cannot return password because it is encrypted
    user_object_for_swift_app['token'] = serializer.dumps({'user_id': user.id})
    # # Token expires in 3600 seconds (1 hour)
    # user_object_for_swift_app['token'] = serializer.dumps({'user_id': user.id}, expires_in=3600)

    user_object_for_swift_app['timezone'] = user.timezone
    user_object_for_swift_app['location_permission_device'] = user.location_permission_device
    user_object_for_swift_app['location_permission_ws'] = user.location_permission_ws
    
    latest_entry = db_session.query(UserLocationDay).filter(UserLocationDay.user_id == user.id) \
                    .order_by(desc(UserLocationDay.date_time_utc_user_check_in)).first()
    if latest_entry != None:
        user_object_for_swift_app['last_location_date'] = str(latest_entry.date_time_utc_user_check_in)[:10]

    return user_object_for_swift_app


def create_data_source_object(current_user, db_session):
    logger_bp_users.info(f"- accessed  create_data_source_object -")


    list_data_source_objects = []

    # user_data_source_json_file_name = f"Dashboard-user_id{current_user.id}.json"
    user_data_source_json_file_name = f"data_source_list_for_user_{current_user.id:04}.json"
    json_data_path_and_name = os.path.join(current_app.config.get('DATA_SOURCE_FILES_DIR'), user_data_source_json_file_name)
    logger_bp_users.info(f"- Dashboard table object file name and path: {json_data_path_and_name} -")
    try:
        if os.path.exists(json_data_path_and_name):
            with open(json_data_path_and_name,'r') as data_source_json_file:
                list_data_source_objects = json.load(data_source_json_file)
                # list_data_source_objects.append(dashboard_table_object)
        else:
            logger_bp_users.info(f"File not found: {json_data_path_and_name}")

            #get user's apple health record count
            # keys to data_source_object_apple_health must match WSiOS DataSourceObject
            data_source_object_apple_health={}
            data_source_object_apple_health['name']="Apple Health Data"
            record_count_apple_health = db_session.query(AppleHealthQuantityCategory).filter_by(user_id=current_user.id).all()
            data_source_object_apple_health['recordCount']="{:,}".format(len(record_count_apple_health))
            # apple_health_record_count, earliest_date_str = get_apple_health_count_date(current_user.id)
            # data_source_object_apple_health['recordCount'] = apple_health_record_count
            # data_source_object_apple_health['earliestRecordDate'] = earliest_date_str
            list_data_source_objects.append(data_source_object_apple_health)
    
        logger_bp_users.info(f"- Returning dashboard_table_object list: {list_data_source_objects} -")
        logger_bp_users.info(f"- END send_data_source_objects -")
        return list_data_source_objects

    except Exception as e:
        logger_bp_users.error(f"An error occurred in send_data_source_objects)")
        logger_bp_users.info(f"{type(e).__name__}: {e}")
        logger_bp_users.info(f"- END send_data_source_objects -")
        return []
