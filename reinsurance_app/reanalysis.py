import threading
import requests
import argparse
import os
import json
import functools
import utils
import ast
import itertools

from flask import Blueprint, Flask, flash, request, session, redirect, url_for, render_template, send_from_directory
from flask_cors import CORS, cross_origin
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_modals import Modal
from reinsurance_math import math_reinsurance
import datetime
from bokeh.models import (HoverTool, FactorRange, Plot, LinearAxis, Grid, Range1d)
from bokeh.models.glyphs import VBar
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models.sources import ColumnDataSource

from config import SERVER_HOST, SERVER_PORT, UPLOAD_FOLDER
from reinsurance_db import api_db
from utils import check_login
from develop_math_method import matplotlibgraph

reanalysis = Blueprint('reanalysis', __name__)

PERIOD_WORK_CONTRACT_MONTH = 50
SMOOTH_INTER = 3


@reanalysis.route('/analysis')
@check_login
def analysis():
    return render_template('analysis.html', contract_status=request.args.get('contract_status'))


@reanalysis.route('/analysis', methods=['POST'])
@check_login
def analysis_results():
    insurance_type_short_title = request.form.get('type_insurance_small_name')
    mdd = request.form.get('mdd')
    period = request.form.get('period')
    kf = request.form.get('kf')
    smooth_inter = request.form.get('smooth_inter')
    work_month = request.form.get('work_month')

    if not insurance_type_short_title or not mdd or not period:
        return redirect(url_for('reanalysis.analysis', contract_status="error"))

    if not kf:
        kf = api_db.get_kf_insurance_type(short_title_insurance_type=insurance_type_short_title)[0]
        if not kf:
            return redirect(url_for('reanalysis.analysis', contract_status="error"))

    kf = float(kf)

    if not smooth_inter:
        smooth_inter = SMOOTH_INTER
    smooth_inter = int(smooth_inter)

    if not work_month:
        work_month = PERIOD_WORK_CONTRACT_MONTH
    work_month = int(work_month)

    mdd = float(mdd)
    period = int(period)

    date_start = (datetime.datetime.today() - datetime.timedelta(days=30 * work_month))
    date_real = datetime.datetime.today()
    list_date_month = utils.list_month_period_back(date_start=date_start, date_real=date_real)

    re_lesion = []
    re_sum = []
    for iter_date in list_date_month:
        var_lesion = \
            api_db.get_lesion_month(short_title_insurance_type=insurance_type_short_title, date_month=iter_date)[0]
        var_sum = api_db.get_sum_month(short_title_insurance_type=insurance_type_short_title, date_month=iter_date)[0]
        if not var_lesion:
            re_lesion.append(0)
        else:
            re_lesion.append(float(var_lesion))
        if not var_sum:
            re_sum.append(0)
        else:
            re_sum.append(float(var_sum))

    data_insurance_type = api_db.get_insurance_type_by_short_title(short_title=insurance_type_short_title)
    start_capital = float(data_insurance_type[3])

    capital, lesion_prediction, sum_prediction = math_reinsurance.forecasting(capital_lesion=re_lesion,
                                                                              sum_contracts=re_sum,
                                                                              last_budget=start_capital,
                                                                              PERIOD_PREDICTION_MONTH=period,
                                                                              SMOOTH_INTER=smooth_inter,
                                                                              KF=kf)

    rec_coefficient = math_reinsurance.calc_recommended_coefficient_insurance(min_allowable_income=mdd,
                                                                              budget_lesion_prediction=lesion_prediction,
                                                                              sum_contracts_prediction=sum_prediction)

    rec_factor = rec_coefficient / kf

    # plot = utils.create_bar_chart(capital, "Оценка видов деятельности", "Месяц", "Капитал", None)
    # script, div = components(plot)

    data_analysis = utils.dict_analysis_value(period_month=period,
                                              capital_start=start_capital,
                                              capital_prediction=capital[-1],
                                              mdd=mdd,
                                              factor=rec_factor,
                                              kf=kf,
                                              kf_prediction=rec_coefficient,
                                              profit=int(capital[-1]) - (start_capital))

    return render_template("analysis.html",
                           contract_status=request.args.get('contract_status'),
                           data_analysis=data_analysis)
