from flask import Blueprint
from flask import request, jsonify, make_response, current_app, g
from ws_models import DatabaseSession, Users, AppleHealthQuantityCategory, \
    AppleHealthWorkout, UserLocationDay, Locations, PendingUsers
from werkzeug.security import generate_password_hash, check_password_hash #password hashing
import bcrypt
from datetime import datetime
from itsdangerous.url_safe import URLSafeTimedSerializer
import logging
import os
from logging.handlers import RotatingFileHandler
import json
import socket
# from app_package.utilsDecorators import token_required, response_dict_tech_difficulties_alert
from app_package._common.token_decorator import token_required
from app_package.bp_users.utils import send_confirm_email, send_reset_email, delete_user_from_table, \
    delete_user_data_files, get_apple_health_count_date, delete_user_daily_csv, \
    create_user_obj_for_swift_login, create_data_source_object, \
    create_dashboard_table_objects, create_new_ambivalent_elf_user, \
    send_confirmation_request_email
# from sqlalchemy import desc
from ws_utilities import convert_lat_lon_to_timezone_string, convert_lat_lon_to_city_country, \
    find_user_location, add_user_loc_day_process
import requests
from app_package._common.utilities import custom_logger, wrap_up_session, save_request_data
import time
import subprocess

logger_bp_users = custom_logger('bp_users.log')
bp_users = Blueprint('bp_users', __name__)
salt = bcrypt.gensalt()



@bp_users.route('/are_we_working', methods=['GET'])
def are_we_working():
    logger_bp_users.info(f"are_we_working endpoint pinged")

    hostname = socket.gethostname()

    return jsonify(f"Yes! We're up! in the {hostname} machine")


@bp_users.route('/login',methods=['POST'])
def login():
    logger_bp_users.info(f"- login endpoint pinged -")
    db_session = g.db_session
    # time.sleep(10)
    #############################################################################################
    ## In case of emergency, ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT prevents users from logging in
    if current_app.config.get('ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT'):
        response_dict = response_dict_tech_difficulties_alert(response_dict = {})
        return jsonify(response_dict)
    #############################################################################################

    # # NOTE: Implement this
    # if request_json.get('ws_api_password') != current_app.config.get('WS_API_PASSWORD'):
    #     logger_bp_users.info(f"- Didn't get the password")
    #     response_dict = {}
    #     response_dict['alert_title'] = ""
    #     response_dict['alert_message'] = f"Invalid API password"
    #     # return jsonify(response_dict)
    #     return jsonify(response_dict), 401

    auth = request.authorization
    logger_bp_users.info(f"- auth.username: {auth.username} -")

    if not auth or not auth.username or not auth.password:
        logger_bp_users.info(f"- /login failed: if not auth or not auth.username or not auth.password")
        return make_response('Could not verify', 401)
    logger_bp_users.info(f"- Checking Broken Pipe error -")
    logger_bp_users.info(f"- db_session ID: {id(db_session)} ")
    user = db_session.query(Users).filter_by(email= auth.username).first()

    if not user:
        logger_bp_users.info(f"- /login failed: if not user:")
        return make_response('Could not verify - user not found', 401)
    
    if auth.password:
        logger_bp_users.info(f"- ******************** -")
        logger_bp_users.info(f"- Check Password -")
        logger_bp_users.info(f"- Check Password -")
        

        logger_bp_users.info(f"- db password (user_exists.password): {user.password.encode()} -")
        logger_bp_users.info(f"- submitted password (auth.password): {auth.password.encode()} -")
        logger_bp_users.info(f"- Check Password -")
        logger_bp_users.info(f"- ******************** -")
        if bcrypt.checkpw(auth.password.encode(), user.password.encode()):
            
            user_object_for_swift_app = create_user_obj_for_swift_login(user, db_session)
            
            response_dict = {}
            response_dict['alert_title'] = "Success"
            response_dict['alert_message'] = ""
            response_dict['user'] = user_object_for_swift_app
            # response_dict['arryDataSourceObjects'] = create_data_source_object(user, db_session)
            data_src_obj_status_str, list_data_source_objects =  create_data_source_object(user, db_session)
            if data_src_obj_status_str == "Success":
                response_dict['arryDataSourceObjects'] = create_data_source_object(user, db_session)
            dash_table_obj_status_str, dashboard_table_object_array = create_dashboard_table_objects(user, db_session)
            if dash_table_obj_status_str == "Success":
                response_dict['arryDashboardTableObjects'] = dashboard_table_object_array
            logger_bp_users.info(f"- response_dict: {response_dict} -")
            return jsonify(response_dict)

    logger_bp_users.info(f"- /login failed: if auth.password:")
    return make_response('Could not verify', 401)



@bp_users.route('/login_generic_account',methods=['POST'])
def login_generic_account():
    logger_bp_users.info(f"- in login_generic_account -")
    # time.sleep(10)
    db_session = g.db_session
    #############################################################################################
    ## In case of emergency, ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT prevents users from logging in
    if current_app.config.get('ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT'):
        response_dict = response_dict_tech_difficulties_alert(response_dict = {})
        return jsonify(response_dict)
    #############################################################################################
    try:
        request_json = request.json
        # logger_bp_users.info(f"username: {request_json.get('username')}")
        logger_bp_users.info(f"user_id: {request_json.get('user_id')}")
    except Exception as e:
        logger_bp_users.info(f"failed to read json")
        logger_bp_users.info(f"{type(e).__name__}: {e}")
        response = jsonify({"error": str(e)})
        return make_response(response, 400)

    if request_json.get('ws_api_password') != current_app.config.get('WS_API_PASSWORD'):
        logger_bp_users.info(f"- Didn't get the password")
        response_dict = {}
        response_dict['alert_title'] = ""
        response_dict['alert_message'] = f"Invalid API password"
        # return jsonify(response_dict)
        return jsonify(response_dict), 401

    # username = request_json.get('username')
    user_id = request_json.get('user_id')
    # user = db_session.query(Users).filter_by(username= username).first()
    user = db_session.get(Users, user_id)

    # # if ambivalent_elf_#### not found in Server Db then make new user 
    if not user:
        logger_bp_users.info(f"- user_id: {user_id} not found.")
        user = create_new_ambivalent_elf_user(db_session)
        logger_bp_users.info(f"- Created new account with Username: {user.username}.")        

    logger_bp_users.info(f"- logging in user: {user}")

    user_object_for_swift_app = create_user_obj_for_swift_login(user, db_session)
    
    response_dict = {}
    response_dict['alert_title'] = "Success"
    response_dict['alert_message'] = ""
    response_dict['user'] = user_object_for_swift_app
    data_src_obj_status_str, list_data_source_objects =  create_data_source_object(user, db_session)
    if data_src_obj_status_str == "Success":
        response_dict['arryDataSourceObjects'] = list_data_source_objects
    dash_table_obj_status_str, dashboard_table_object_array = create_dashboard_table_objects(user, db_session)
    if dash_table_obj_status_str == "Success":
        response_dict['arryDashboardTableObjects'] = dashboard_table_object_array
    logger_bp_users.info(f"- response_dict: {response_dict} -")
    return jsonify(response_dict)

# I don't think this is used 2024-10-12
# - analyzed using the UserStore.connectDevice() method that only /login, /login_generic_account, and 
#    /register_generic_account are the only ones called. It doesn't seem /register is ever called.
@bp_users.route('/register', methods=['POST'])
def register():
    logger_bp_users.info(f"- register endpoint pinged -")
    logger_bp_users.info(request.json)
    db_session = g.db_session

    ######################################################################################
    ## In case of emergency, ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT prevents new users
    if current_app.config.get('ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT'):
        response_dict = response_dict_tech_difficulties_alert(response_dict = {})
        return jsonify(response_dict)
    ######################################################################################

    try:
        request_json = request.json
        logger_bp_users.info(f"successfully read request_json (email): {request_json.get('email')}")
    except Exception as e:
        logger_bp_users.info(f"failed to read json")
        logger_bp_users.info(f"{type(e).__name__}: {e}")
        response = jsonify({"error": str(e)})
        return make_response(response, 400)
    

    if request_json.get('ws_api_password') != current_app.config.get('WS_API_PASSWORD'):
        response_dict = {}
        response_dict['alert_title'] = ""
        response_dict['alert_message'] = f"Requests not from What Sticks Platform applications will not be supported."
        # return jsonify(response_dict)
        return jsonify({'error': 'Invalid API password'}), 401

    if request_json.get('email') in ("", None) or request_json.get('new_password') in ("" , None):
        logger_bp_users.info(f"- failed register no email or password -")
        response_dict["alert_title"] = f"User must have email and password"
        response_dict["alert_message"] = f""
        return jsonify(response_dict)

    user_exists = db_session.query(Users).filter_by(email= request_json.get('email')).first()

    if user_exists:
        logger_bp_users.info(f"- failed register user already exists -")
        response_dict["alert_title"] = f"User already exists"
        response_dict["alert_message"] = f"Try loggining in"
        return jsonify(response_dict)

    hash_pw = bcrypt.hashpw(request_json.get('new_password').encode(), salt)
    new_user = Users()

    for key, value in request_json.items():
        if key == "new_password":
            setattr(new_user, "password", hash_pw)
        elif key == "email":
            setattr(new_user, "email", request_json.get('email'))

    setattr(new_user, "timezone", "Etc/GMT")

    db_session.add(new_user)
    db_session.flush()
    # wrap_up_session(logger_bp_users)
    logger_bp_users.info(f"- Successfully registered {new_user.email} as user id: {new_user.id}  -")

 
    if request_json.get('email') not in current_app.config.get('LIST_NO_CONFIRMASTION_EMAILS'):
        send_confirm_email(request_json.get('email'))

    response_dict = {}
    response_dict["message"] = f"new user created: {request_json.get('email')}"
    response_dict["id"] = f"{new_user.id}"
    response_dict["username"] = f"{new_user.username}"
    response_dict["alert_title"] = f"Success!"
    response_dict["alert_message"] = f""
    logger_bp_users.info(f"- Successfully registered response_dict: {response_dict}  -")
    return jsonify(response_dict)


@bp_users.route('/register_generic_account', methods=['POST'])
def register_generic_account():
    logger_bp_users.info(f"- in register_generic_account -")
    db_session = g.db_session

    ######################################################################################
    ## In case of emergency, ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT prevents new users
    if current_app.config.get('ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT'):
        response_dict = response_dict_tech_difficulties_alert(response_dict = {})
        return jsonify(response_dict)
    ######################################################################################
    
    if request.json.get('ws_api_password') != current_app.config.get('WS_API_PASSWORD'):
        response_dict = {}
        response_dict['alert_title'] = ""
        response_dict['alert_message'] = f"Requests not from What Sticks Platform applications will not be supported."
        # return jsonify(response_dict)
        return jsonify({'error': 'Invalid API password'}), 401

    new_user = create_new_ambivalent_elf_user(db_session)
    user_object_for_swift_app = create_user_obj_for_swift_login(new_user, db_session)
    
    response_dict = {}
    response_dict['alert_title'] = "Success"
    response_dict['alert_message'] = "are we right?"
    # response_dict['id'] = "the numbrer 4"
    response_dict['user'] = user_object_for_swift_app
    response_dict["id"] = f"{new_user.id}"
    response_dict["username"] = f"{new_user.username}"
    logger_bp_users.info(f"- Successfully registered response_dict: {response_dict}  -")
    return jsonify(response_dict)
        

@bp_users.route('/convert_generic_account_to_custom_account', methods=['POST'])
@token_required
def convert_generic_account_to_custom_account(current_user):
    
    logger_bp_users.info(f"- in convert_generic_account_to_custom_account -")
    # ws_api_password = request.json.get('WS_API_PASSWORD')
    # logger_bp_users.info(request.json)
    db_session = g.db_session
    # time.sleep(5) 

    ######################################################################################
    ## In case of emergency, ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT prevents new users
    if current_app.config.get('ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT'):
        response_dict = response_dict_tech_difficulties_alert(response_dict = {})
        return jsonify(response_dict)
    ######################################################################################   

    if request.json.get('ws_api_password') != current_app.config.get('WS_API_PASSWORD'):
        response_dict = {}
        response_dict['alert_title'] = ""
        response_dict['alert_message'] = f"Requests not from What Sticks Platform applications will not be supported."
        return jsonify({'error': 'Invalid API password'}), 401
    
    auth = request.authorization

    new_email = auth.username
    new_password = auth.password

    logger_bp_users.info(f"- new_email (auth.username): {new_email} -")
    logger_bp_users.info(f"- new_password (auth.password): {new_password} -")

    if new_email in ("", None) or new_password in ("" , None):
        logger_bp_users.info(f"- failed register no email or password -")
        response_dict["alert_title"] = f"User must have email and password"
        response_dict["alert_message"] = f""
        return jsonify(response_dict)

    user_exists = db_session.query(Users).filter_by(email= new_email).first()

    logger_bp_users.info(f"- user_exists: {user_exists} -")

    if user_exists:
        logger_bp_users.info(f"- PASSED if user_exists: -")
        logger_bp_users.info(f"- db password: {user_exists.password.encode()} -")
        logger_bp_users.info(f"- submitted password: {new_password.encode()} -")
        
        if bcrypt.checkpw(new_password.encode(), user_exists.password.encode()):
            logger_bp_users.info(f"- PASSED if bcrypt.checkpw(auth.password.encode(), -")
            #################################
            # check if this user has data search for data_source_json file
            current_user_data_source_json_file_name = f"data_source_list_for_user_{current_user.id:04}.json"
            current_user_data_source_json_file = os.path.join(current_app.config.get('DATA_SOURCE_FILES_DIR'), current_user_data_source_json_file_name)


            existing_user_data_source_json_file_name = f"data_source_list_for_user_{user_exists.id:04}.json"
            existing_user_data_source_json_file = os.path.join(current_app.config.get('DATA_SOURCE_FILES_DIR'), existing_user_data_source_json_file_name)

            logger_bp_users.info(f"- current_user_data_source_json_file exists?: {os.path.exists(current_user_data_source_json_file)} -")
            logger_bp_users.info(f"- existing_user_data_source_json_file exists?: {os.path.exists(existing_user_data_source_json_file)} -")
            



            # This means the current_user (ambivalent_elf_###) has NO data and existing_user (new_email) HAS data
            ## only case where delete current_user (ambivalent_elf_####)
            if not os.path.exists(current_user_data_source_json_file) and os.path.exists(existing_user_data_source_json_file):
                #################################
                # Change user to old account
                # Step 1: Create New token and place in user_object_for_swift_app with old account id
                user_object_for_swift_app = create_user_obj_for_swift_login(user_exists, db_session)
                
                logger_bp_users.info(f"- Changed Token -")
                #################################
                # Step 2: Check for old Data Source JSON
                user_data_source_json_file_name = f"data_source_list_for_user_{user_exists.id:04}.json"
                json_data_path_and_name = os.path.join(current_app.config.get('DATA_SOURCE_FILES_DIR'), user_data_source_json_file_name)
                data_source_object_array = []
                if os.path.exists(json_data_path_and_name):
                    with open(json_data_path_and_name,'r') as data_source_json_file:
                        data_source_object_array = json.load(data_source_json_file)
                #################################
                # Step 3: Check for old Dashboard Table JSON
                user_data_table_array_json_file_name = f"data_table_objects_array_{user_exists.id:04}.json"
                json_data_path_and_name = os.path.join(current_app.config.get('DASHBOARD_FILES_DIR'), user_data_table_array_json_file_name)
                logger_bp_users.info(f"- Dashboard table object file name and path: {json_data_path_and_name} -")
                dashboard_table_object_array = []
                logger_bp_users.info(f"- os.path.exists(json_data_path_and_name): {os.path.exists(json_data_path_and_name)} -")
                logger_bp_users.info(f"- json_data_path_and_name: {json_data_path_and_name} -")
                if os.path.exists(json_data_path_and_name):
                    logger_bp_users.info(f"- Changed Token -")
                    with open(json_data_path_and_name,'r') as dashboard_json_file:
                        dashboard_table_object_array = json.load(dashboard_json_file)
                

                #################################
                # Step 4: delete current_user (ambivalent_elf_###)
                delete_apple_health_qty_cat = delete_user_from_table(current_user, AppleHealthQuantityCategory)
                delete_apple_health_workouts = delete_user_from_table(current_user, AppleHealthWorkout)
                delete_user_location_day = delete_user_from_table(current_user, UserLocationDay)
                # delete: dataframe pickle, data source json, and dashboard json
                delete_user_data_files(current_user)
                # delete user daily CSV files that display on the website user home page:
                delete_user_daily_csv(current_user)
                delete_user_from_users_table = delete_user_from_table(current_user, Users)


                #################################
                # Step 5: Send back 
                response_dict = {}
                response_dict['alert_title'] = "Success!"
                response_dict['alert_message'] = ""
                response_dict['user'] = user_object_for_swift_app
                response_dict['data_source_object_array'] = data_source_object_array
                response_dict['dashboard_table_object_array'] = dashboard_table_object_array

                logger_bp_users.info(f"- response_dict: {response_dict} -")
                return jsonify(response_dict)


            # This means the current account (ambivalent_elf_###) has data OR the existing_user (new_email) has NO data
            else:
                #################################
                # Step 1: delete old account
                delete_apple_health_qty_cat = delete_user_from_table(user_exists, AppleHealthQuantityCategory)
                delete_apple_health_workouts = delete_user_from_table(user_exists, AppleHealthWorkout)
                delete_user_location_day = delete_user_from_table(user_exists, UserLocationDay)
                # delete: dataframe pickle, data source json, and dashboard json
                delete_user_data_files(user_exists)
                # delete user daily CSV files that display on the website user home page:
                delete_user_daily_csv(user_exists)
                delete_user_from_users_table = delete_user_from_table(user_exists, Users)

                #################################
                # Step 2: Update user generic
                current_user.email = new_email
                current_user.username = new_email.split('@')[0]
                hash_pw = bcrypt.hashpw(new_password.encode(), salt)
                current_user.password = hash_pw
                db_session.flush()
                user_object_for_swift_app = create_user_obj_for_swift_login(current_user, db_session)
                if new_email not in current_app.config.get('LIST_NO_CONFIRMASTION_EMAILS'):
                    send_confirm_email(new_email)

                response_dict = {}
                response_dict["message"] = f"new user created: {new_email}"
                response_dict['user'] = user_object_for_swift_app
                response_dict["alert_title"] = f"Success!"
                response_dict["alert_message"] = f""
                logger_bp_users.info(f"- Successfully converted acccount response_dict: {response_dict}  -")
                return jsonify(response_dict)



        
        else:
            logger_bp_users.info(f"- failed register user already exists -")
            response_dict["alert_title"] = f"Email already exists"
            response_dict["alert_message"] = f"passwords not matching"
            return jsonify(response_dict), 409
    else:
        #################################
        # Update UsersPending table
        # send email with verification
        # current_user.email = new_email
        # current_user.username = new_email.split('@')[0]
        pending_user = db_session.get(PendingUsers,current_user.id)
        if pending_user:
            delete_user_from_users_table = delete_user_from_table(current_user, PendingUsers)

        new_pending_user = PendingUsers(user_id=current_user.id, email = new_email)
        hash_pw = bcrypt.hashpw(new_password.encode(), salt)
        new_pending_user.password = hash_pw
        db_session.add(new_pending_user)
        db_session.flush()

        # if new_email not in current_app.config.get('LIST_NO_CONFIRMASTION_EMAILS'):
        #     send_confirm_email(new_email)
        # serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        serializer = URLSafeTimedSerializer(current_app.config.get('SECRET_KEY'))
        serialized_token = serializer.dumps({'user_id': current_user.id})

        # url_for_confirmation = request.base_url
        host_url = request.host_url
        logger_bp_users.info(f"- host_url: {host_url} -")
        logger_bp_users.info(f"- host_url (type): {type(host_url)} -")

        send_confirmation_request_email(new_email, serialized_token, host_url)

        response_dict = {}
        response_dict["message"] = f"Check email and validate this request: {new_email}"
        # response_dict['user'] = user_object_for_swift_app
        response_dict["alert_title"] = f"Success!"
        response_dict["alert_message"] = f"Check email and validate this request: {new_email}"
        logger_bp_users.info(f"- Successfully converted account response_dict: {response_dict}  -")
        return jsonify(response_dict)


@bp_users.route("/receive_email_validation/<serialized_token>", methods=["GET"])
def receive_email_validation(serialized_token):
    logger_bp_users.info(f"- in receive_email_validation  ---")
    logger_bp_users.info(f"- serialized_token: {serialized_token}  ---")
    db_session = g.db_session
    serializer = URLSafeTimedSerializer(current_app.config.get('SECRET_KEY'))
    response_dict = {}

    try:
        payload = serializer.loads(serialized_token, max_age=1000)
        user_id = payload.get("user_id")
        logger_bp_users.info(f"- payload: {payload}  ---")
        logger_bp_users.info(f"- user_id: {user_id}  ---")
    except Exception as e:
        logger_bp_users.info(f"failed to read token")
        logger_bp_users.info(f"{type(e).__name__}: {e}")
        
        response_dict['alert_title'] = ""
        response_dict['alert_message'] = f"Invalid Token"
        return jsonify(response_dict), 401
    
    try: 
        # pending_user = db_session.get(PendingUsers,user_id)
        pending_user = db_session.query(PendingUsers).filter_by(user_id= user_id).first()
    except Exception as e:
        logger_bp_users.info(f"failed to find Pending User")
        logger_bp_users.info(f"{type(e).__name__}: {e}")
        # response_dict = {}
        response_dict['alert_title'] = ""
        response_dict['alert_message'] = f"Failed to find Pending User"
        # return jsonify(response_dict)
        return jsonify(response_dict), 401

    existing_user = db_session.query(Users).filter_by(id= user_id).first()
    existing_user.email = pending_user.email
    existing_user.username = pending_user.email.split('@')[0]
    existing_user.password = pending_user.password
    db_session.flush()
    user_object_for_swift_app = create_user_obj_for_swift_login(existing_user, db_session)

    delete_user_from_users_table = delete_user_from_table(existing_user, PendingUsers)
    # response_dict = {}
    response_dict["message"] = f"User updated: {existing_user.email}"
    response_dict['user'] = user_object_for_swift_app
    response_dict["alert_title"] = f"Successfully updated user!"
    response_dict['alert_message'] = f""
    logger_bp_users.info(f"- response_dict: {response_dict}")
    return jsonify(response_dict)


# this get's sent at login
@bp_users.route('/send_data_source_objects', methods=['GET'])
@token_required
def send_data_source_objects(current_user):
    logger_bp_users.info(f"- accessed  send_data_source_objects endpoint-")
    db_session = g.db_session

    data_src_obj_status_str, list_data_source_objects = create_data_source_object(current_user, db_session)

    match data_src_obj_status_str:
        case "Could be anything":
            return jsonify({"error": "An unexpected error occurred"}), 500
        case "Success":
            return jsonify(list_data_source_objects)


@bp_users.route('/send_dashboard_table_objects', methods=['GET'])
@token_required
def send_dashboard_table_objects(current_user):
    logger_bp_users.info(f"- accessed  send_dashboard_table_objects endpoint-")
    db_session = g.db_session

    dash_table_obj_status_str, dashboard_table_object_array = create_dashboard_table_objects(current_user, db_session)
    match dash_table_obj_status_str:
        case "File not found":
            return jsonify({"error": 
                f"No data_table_objects_array_{current_user.id:04}.json file exists on Server"}), 404
        case "Could be anything":
            return jsonify({"error": "An unexpected error occurred"}), 500
        case "Success":
            return jsonify(dashboard_table_object_array)

# Designed for iOS DashboardVC pull down response
@bp_users.route('/send_both_data_source_and_dashboard_objects', methods=['GET'])
@token_required
def send_both_data_source_and_dashboard_objects(current_user):
    logger_bp_users.info(f"- ***** accessed  send_both_data_source_and_dashboard_objects endpoint-")
    db_session = g.db_session

    user_object_for_swift_app = create_user_obj_for_swift_login(current_user, db_session)
    
    response_dict = {}
    response_dict['alert_title'] = "Success"
    response_dict['alert_message'] = ""
    response_dict['user'] = user_object_for_swift_app

    #NOTE: Do not send one without the other -> important for the mobile app

    data_src_obj_status_str, list_data_source_objects =  create_data_source_object(current_user, db_session)
    # if data_src_obj_status_str == "Success":
    #     response_dict['arryDataSourceObjects'] = list_data_source_objects

    dash_table_obj_status_str, dashboard_table_object_array = create_dashboard_table_objects(current_user, db_session)
    if dash_table_obj_status_str == "Success" and data_src_obj_status_str == "Success":
        response_dict['arryDataSourceObjects'] = list_data_source_objects
        response_dict['arryDashboardTableObjects'] = dashboard_table_object_array



    return jsonify(response_dict)



# this get's sent at login
@bp_users.route('/delete_user', methods=['GET'])
@token_required
def delete_user(current_user):
    logger_bp_users.info(f"- accessed  delete_user endpoint-")
    db_session = g.db_session
    deleted_records = 0

    # delete_apple_health = delete_user_from_table(current_user, AppleHealthQuantityCategory)
    delete_apple_health_qty_cat = delete_user_from_table(current_user, AppleHealthQuantityCategory)
    if delete_apple_health_qty_cat[1]:
        logger_bp_users.info(f"- Error trying to delete AppleHealthQuantityCategory for user {current_user.id}, error: {delete_apple_health_qty_cat[1]} -")
        response_message = f"- Error trying to delete AppleHealthQuantityCategory for user {current_user.id}, error: {delete_apple_health_qty_cat[1]}"
        return make_response(jsonify({"error":response_message}), 500)
    
    deleted_records = delete_apple_health_qty_cat[0]

    delete_apple_health_workouts = delete_user_from_table(current_user, AppleHealthWorkout)
    if delete_apple_health_workouts[1]:
        logger_bp_users.info(f"- Error trying to delete AppleHealthQuantityCategory for user {current_user.id}, error: {delete_apple_health_workouts[1]} -")
        response_message = f"- Error trying to delete AppleHealthQuantityCategory for user {current_user.id}, error: {delete_apple_health_workouts[1]}"
        return make_response(jsonify({"error":response_message}), 500)
    
    deleted_records = delete_apple_health_workouts[0]


    delete_user_location_day = delete_user_from_table(current_user, UserLocationDay)
    # if delete_oura_token[1]:
    #     logger_bp_users.info(f"- Error trying to delete UserLocationDay for user {current_user.id}, error: {delete_oura_token[1]} -")
    #     response_message = f"Error trying to delete UserLocationDay for user {current_user.id}, error: {delete_oura_token[1]} "
    #     return make_response(jsonify({"error":response_message}), 500)

    deleted_records += delete_user_location_day[0]

    # delete: dataframe pickle, data source json, and dashboard json
    delete_user_data_files(current_user)
    # delete user daily CSV files that display on the website user home page:
    delete_user_daily_csv(current_user)

    # delete user
    delete_user_from_users_table = delete_user_from_table(current_user, Users)
    if delete_user_from_users_table[1]:
        logger_bp_users.info(f"- Error trying to delete Users for user {current_user.id}, error: {delete_user_from_users_table[1]} -")
        response_message = f"Error trying to delete Users for user {current_user.id}, error: {delete_user_from_users_table[1]} "
        return make_response(jsonify({"error":response_message}), 500)

    deleted_records += delete_user_from_users_table[0]
    db_session.flush()

    response_dict = {}
    response_dict['message'] = "Successful deletion."
    response_dict['count_deleted_rows'] = "{:,}".format(deleted_records)

    # Create new generic user
    logger_bp_users.info(f"- setting up the real ambiv_elf_#### -")
    new_username = "ambivalent_elf_"
    new_user = Users(username=new_username)
    #Add user to get user_id
    db_session.add(new_user)
    db_session.flush()
    user_id = new_user.id
    new_username = "ambivalent_elf_"+f"{user_id:04}"
    new_user.username = new_username
    logger_bp_users.info(f"- new user is {new_username} -")
    user_object_for_swift_app = create_user_obj_for_swift_login(new_user, db_session)
    response_dict['user'] = user_object_for_swift_app

    logger_bp_users.info(f"- response_dict: {response_dict} -")
    return jsonify(response_dict)


# @bp_users.route('/reset_password', methods = ["GET", "POST"])
@bp_users.route('/get_reset_password_token', methods = ["GET", "POST"])
def get_reset_password_token():
    logger_bp_users.info(f"- accessed: get_reset_password_token endpoint pinged -")
    db_session = g.db_session
    logger_bp_users.info(request.json)
    #############################################################################################
    ## In case of emergency, ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT prevents users from logging in
    if current_app.config.get('ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT'):
        response_dict = response_dict_tech_difficulties_alert(response_dict = {})
        return jsonify(response_dict)
    #############################################################################################
    

    try:
        request_json = request.json
        logger_bp_users.info(f"request_json: {request_json}")
    except Exception as e:
        logger_bp_users.info(f"failed to read json")
        logger_bp_users.info(f"{type(e).__name__}: {e}")
        response = jsonify({"error": str(e)})
        return make_response(response, 400)


    if current_app.config.get('WS_API_PASSWORD') != request_json.get('ws_api_password'):
        response_dict = {}
        response_dict['alert_title'] = ""
        response_dict['alert_message'] = f"Requests not from What Sticks Platform applications will not be supported."

        return jsonify(response_dict)

    # if request.method == 'POST':
    # formDict = request.form.to_dict()
    email = request_json.get('email')
    user = db_session.query(Users).filter_by(email=email).first()
    logger_bp_users.info(f"- user: {user} -")
    if user:
        logger_bp_users.info('Email reaquested to reset: ', email)
        send_reset_email(user)
        response_dict = {}
        response_dict['alert_title'] = "Success"
        response_dict['alert_message'] = f"Email sent to {email} with reset information"
        return jsonify(response_dict)

    else:
        response_dict = {}
        response_dict['alert_title'] = "Success"
        response_dict['alert_message'] = f" {email} has no account with What Sticks"

        return jsonify(response_dict)


@bp_users.route('/reset_password', methods = ["POST"])
@token_required
def reset_password(current_user):
    # db_session = g.db_session
    logger_bp_users.info(f"- accessed: reset_password with token")
    try:
        request_json = request.json
        logger_bp_users.info(f"successfully read request_json: {request_json}")
    except Exception as e:
        logger_bp_users.info(f"failed to read json")
        logger_bp_users.info(f"{type(e).__name__}: {e}")
        response = jsonify({"error": str(e)})
        return make_response(response, 400)

    if current_user:
        logger_bp_users.info(f"---- > in if current_user")
        hash_pw = bcrypt.hashpw(request_json.get('password_text').encode(), salt)
        # user = db_session.get(Users, current_user.id)
        logger_bp_users.info(f"user: {current_user}")
        current_user.password = hash_pw
        # user.password = hash_pw
        # db_session.commit()
        # sess.commit()
        logger_bp_users.info(f"**** ************************ ******")
        logger_bp_users.info(f"**** changed current user and removed sess.commit() ******")
        logger_bp_users.info(f"**** committing new password ******")
        logger_bp_users.info(f"**** ************************ ******")

        response_dict = {}
        response_dict['alert_title'] = "Success"
        response_dict['alert_message'] = f" {current_user.username}'s password has been reset"

        return jsonify(response_dict)
    else:
        response_dict = {}
        response_dict['alert_title'] = "Failed"
        response_dict['alert_message'] = f" {current_user.username}'s password has NOT been reset"

        return jsonify(response_dict)


# This replaces /update_user_location_with_lat_lon AND /update_user_location_with_user_location_json
@bp_users.route('/update_user_location_details', methods=["POST"])
@token_required
def update_user_location_details(current_user):
    logger_bp_users.info(f"- in update_user_location_details -")
    db_session = g.db_session

    try:
        request_json = request.json
        logger_bp_users.info(f"request_json: {request_json}")
        save_request_data(request_json, request.path, current_user.id,
                            current_app.config.get('USER_LOCATION_JSON'), logger_bp_users)

    except Exception as e:
        logger_bp_users.info(f"failed to read json in update_user_location_with_user_location_json")
        logger_bp_users.info(f"{type(e).__name__}: {e}")
        response = jsonify({"error": str(e)})
        return make_response(response, 400)
    
    logger_bp_users.info(f"- WHAT ARE location_permission_device and location_permission_ws ???-")
    logger_bp_users.info(f"- location_permission_device: {request_json.get('location_permission_device')}, {type(request_json.get('location_permission_device'))}-")
    logger_bp_users.info(f"- location_permission_ws: {request_json.get('location_permission_ws')}, {type(request_json.get('location_permission_ws'))}-")
    
    # NOTE: location_permission_device set everytime iOS app is launched in LocationFetcher (i.e. will never be null when request sent)
    # - location_permission_ws set everytime the iOS app UISwitch is toggled > before (and the only times) this route is accessed (i.e. also never null)

    current_user.location_permission_device=request_json.get('location_permission_device')
    current_user.location_permission_ws=request_json.get('location_permission_ws')

    user_object_for_swift_app = create_user_obj_for_swift_login(current_user, db_session)

    # recieve user_location.json and update UserLocDay
    user_location_list = request_json.get('user_location')
    if user_location_list:
        logger_bp_users.info(f"- ADDing User Location Day -")
        user_loction_filename = f"user_location-user_id{current_user.id}.json"
        json_data_path_and_name = os.path.join(current_app.config.get('USER_LOCATION_JSON'),user_loction_filename)

        with open(json_data_path_and_name, 'w') as file:
            json.dump(user_location_list, file, indent=4)
        
        for location in user_location_list:
            formatted_datetime_utc = location.get('timestampString')
            latitude = location.get('latitude')
            longitude = location.get('longitude')
            add_user_loc_day_process(db_session, current_user.id, latitude, longitude, formatted_datetime_utc)

        # add_user_loc_day_process already flushes locations
        # db_session.flush()

        # Use userLocDay to update user Table User table timezone
        for count, loc_day in enumerate(db_session.get(Users,current_user.id).loc_day):
            if count == 0:
                most_current_date = loc_day.date_utc_user_check_in
                most_current_date_timezone_str = db_session.get(Locations,loc_day.location_id).tz_id
            elif loc_day.date_utc_user_check_in > most_current_date:
                most_current_date = loc_day.date_utc_user_check_in
                most_current_date_timezone_str = db_session.get(Locations,loc_day.location_id).tz_id

        current_user.timezone = most_current_date_timezone_str

    response_dict = {}

    # check if dashbaord json file exits
    user_data_table_array_json_file_name = f"data_table_objects_array_{current_user.id:04}.json"
    json_data_path_and_name = os.path.join(current_app.config.get('DASHBOARD_FILES_DIR'), user_data_table_array_json_file_name)
    if os.path.exists(json_data_path_and_name):
        logger_bp_users.info(f"---> found: json_data_path_and_name 📢-")
        #if exists 
        path_sub = os.path.join(current_app.config.get('APPLE_SERVICE_11_ROOT'), 'send_job.py')
        # run WSAS subprocess
        logger_bp_users.info(f"---> SENDING subprocess ['python', path_sub, user_id_string, time_stamp_str_for_json_file_name, 'False', 'False'] -")
        user_id_string = str(current_user.id)
        time_stamp_str_for_json_file_name = "just_recalculate"
        process = subprocess.Popen(['python', path_sub, user_id_string, time_stamp_str_for_json_file_name, 'False', 'False'])
        logger_bp_users.info(f"---> successfully started subprocess PID:: {process.pid} -")


    logger_bp_users.info(f"- successfully finished /update_user_location_details route -")
    response_dict['alert_title'] = "Success!"# < -- This is expected response for WSiOS to delete old user_locations.json
    response_dict['alert_message'] = ""
    try:
        response_dict['user'] = user_object_for_swift_app
    except:
        logger_bp_users.info(f"- no update to user table -")

    return jsonify(response_dict)





