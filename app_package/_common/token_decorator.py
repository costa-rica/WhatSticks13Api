from functools import wraps
from flask import request, jsonify,current_app,g
# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous.url_safe import URLSafeTimedSerializer#new 2023
from ws_models import DatabaseSession, Users
import logging
import os
from logging.handlers import RotatingFileHandler
from app_package._common.utilities import custom_logger, wrap_up_session

logger_token_decorator = custom_logger("token_decorator.log")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        logger_token_decorator.info(f'- token_required decorator accessed -')
        # db_session = DatabaseSession()
        # g.db_session = db_session  # In the token_required decorator
        db_session = g.db_session
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
            # print('x-access-token exists!!')
            logger_token_decorator.info(f'- x-access-token exists!! -')
            
        if not token:
            logger_token_decorator.info(f'- no token -')
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            decrypted_token_dict = serializer.loads(token)
            logger_token_decorator.info(f'- decrypted_token_dict: {decrypted_token_dict} -')
            logger_token_decorator.info('----')
            logger_token_decorator.info(decrypted_token_dict['user_id'])
            logger_token_decorator.info(db_session.get(Users,int(decrypted_token_dict['user_id'])))
            logger_token_decorator.info('----')
            current_user = db_session.get(Users,int(decrypted_token_dict['user_id']))
            logger_token_decorator.info(f'- token decrypted correctly -')
            # wrap_up_session(logger_token_decorator, db_session)
        except Exception as e:
            logger_token_decorator.info(f"- token NOT decrypted correctly -")
            logger_token_decorator.info(f"- {type(e).__name__}: {e} -")
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated


