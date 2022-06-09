import threading
import requests
import argparse
import os
import json
import functools

from flask import Blueprint, Flask, flash, request, session, redirect, url_for, render_template, send_from_directory
from flask_cors import CORS, cross_origin
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from config import SERVER_HOST, SERVER_PORT, UPLOAD_FOLDER
from reinsurance_db import api_db
from utils import check_login

main = Blueprint('main', __name__)


@main.route('/')
@check_login
def index():
    return render_template('index.html')


@main.route('/profile')
@check_login
def profile():
    return render_template('profile.html')


@main.route('/shutdown')
def shutdown():
    terminate_func = request.environ.get('werkzeug.server.shutdown')
    if terminate_func:
        terminate_func()


@main.route('/contracts', methods=['GET'])
@check_login
def contracts():
    _contracts = api_db.get_contracts()
    return render_template('contracts.html', contracts_list=_contracts)
    # return render_template('contract_update.html')
    # return render_template('contracts.html')


@main.route('/contracts/add', methods=['GET'])
@check_login
def contracts_add():
    return render_template('contract_update.html')


@main.route('/contracts/add', methods=['POST'])
@check_login
def contracts_add_post():

    company_name = request.form.get('company_name')
    id_company = api_db.getid_company(name=company_name)
    if id_company:
        contract_create = api_db.update_company(name=company_name, idcompany=id_company)
    else:
        contract_create = api_db.add_company(name=company_name)
        id_company = api_db.getid_company(name=company_name)
    if not contract_create: return render_template('contract_update.html', contract_status="error")

    passport_series = request.form.get('client_passport_series')
    passport_id = request.form.get('client_passport_id')
    id_client = api_db.getid_client(passport_series=passport_series, passport_id=passport_id)
    if id_client:
        contract_create = api_db.update_client(name=request.form.get('client_name'),
                                               surname=request.form.get('client_surname'),
                                               sec_name=request.form.get('client_sec_name'),
                                               passport_series=passport_series,
                                               passport_id=passport_id,
                                               idclient=id_client)
    else:
        contract_create = api_db.add_client(name=request.form.get('client_name'),
                                            surname=request.form.get('client_surname'),
                                            sec_name=request.form.get('client_sec_name'),
                                            passport_series=passport_series,
                                            passport_id=passport_id)
        id_client = api_db.getid_client(passport_series=passport_series, passport_id=passport_id)
    if not contract_create: return render_template('contract_update.html', contract_status="error")

    title = request.form.get('client_passport_id')
    short_title = request.form.get('type_insurance_small_name')
    id_insurance_type = api_db.getid_insurance_type(title=title)
    if id_insurance_type:
        contract_create = api_db.update_insurance_type(title=title,
                                                       short_title=request.form.get('type_insurance_small_name'),
                                                       capital=request.form.get('type_insurance_capital'),
                                                       idinsurance_type=id_insurance_type)
    else:
        contract_create = api_db.add_insurance_type(title=title,
                                                    short_title=request.form.get('type_insurance_small_name'),
                                                    capital=request.form.get('type_insurance_capital'))
        id_insurance_type = api_db.getid_insurance_type(title=title)
    if not contract_create: return render_template('contract_update.html', contract_status="error")

    insurance_amount = request.form.get('insurance_amount')
    insurance_payment = request.form.get('insurance_payment')
    date_start = request.form.get('date_start')
    date_stop = request.form.get('date_stop')
    id_unit = api_db.getid_default_unit()
    id_agent = session['idagent']

    id_contract = api_db.getid_contract(id_client=id_client)
    if id_contract:
        api_db.update_contract(id_client=id_client,
                               id_company=id_company,
                               id_unit=id_unit,
                               id_insurance_type=id_insurance_type,
                               id_agent=id_agent,
                               insurance_amount=insurance_amount,
                               insurance_payment=insurance_payment,
                               date_start=date_start,
                               date_stop=date_stop,
                               idcontract=id_contract)
        return render_template('contract_update.html', contract_status="update")
    else:
        api_db.add_contract(id_client=id_client,
                            id_company=id_company,
                            id_unit=id_unit,
                            id_insurance_type=id_insurance_type,
                            id_agent=id_agent,
                            insurance_amount=insurance_amount,
                            insurance_payment=insurance_payment,
                            date_start=date_start,
                            date_stop=date_stop)

        return render_template('contract_update.html', contract_status="create")
