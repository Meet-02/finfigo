import os
import re
import mysql.connector
from flask import Flask, request, render_template, redirect, flash, url_for, session, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai
from calc_job import calc_job_tax_new_regime
from calc_bus import calc_bus_tax_new_regime
from calc_gst import calculate_gst
from pdf_gen import create_tax_report as create_job_report
from bus_pdf_gen import create_tax_report as create_business_report
from database.mydata_db import get_connection
import datetime

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_12345'

load_dotenv()

# Configure Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not found in .env file. AI features will be disabled.")

# --- Database Configuration (Left as placeholder, uses get_connection) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.join(BASE_DIR, 'database')
db_path = os.path.join(db_dir, 'mydata.db')

# --- Helper Function ---
def get_float(key):
    try:
        return float(request.form.get(key, 0) or 0)
    except (ValueError, TypeError):
        return 0.0

# ===================================================================
# --- General and User Management Routes ---
# ===================================================================
@app.route('/')
def landing():
    return render_template('landingpage.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        pan = request.form.get('PAN')
        password = request.form.get('pass')
        if not pan or not password:
            flash("Please fill in all details!")
            return redirect(url_for('signup'))
        with get_connection(autocommit=True) as conn:
            with conn.cursor(buffered=True) as cur:
                try:
                    cur.execute('INSERT INTO user (pan_id, password) VALUES (%s, %s)', (pan, generate_password_hash(password)))
                    try:
                        cur.fetchall()
                    except mysql.connector.InterfaceError:
                        pass
                    flash("Signup successful! Please log in.")
                    return redirect(url_for('signup'))
                except mysql.connector.IntegrityError:
                    flash("This PAN number is already registered.")
                    return redirect(url_for('signup'))
    return render_template('sign-up.html')

@app.route('/login', methods=['POST'])
def login():
    pan = request.form.get('PAN')
    password = request.form.get('pass')
    with get_connection(autocommit=True) as conn:
        with conn.cursor(buffered=True) as cur:
            cur.execute('SELECT * FROM user WHERE pan_id = %s', (pan,))
            user = cur.fetchone()
            cur.fetchall()
            if user and check_password_hash(user[2], password):
                flash("Login successful!")
                session.clear()
                session['pan_id'] = pan
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid PAN or password.")
                return redirect(url_for('signup'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.")
    return redirect(url_for('landing'))

# --- Dashboard and Category Selection ---
@app.route('/dashboard')
def dashboard():
    if 'pan_id' not in session:
        return redirect(url_for('signup'))

    with get_connection() as conn:
        with conn.cursor(buffered=True) as cur:
            cur.execute('SELECT person_id FROM user_pan_mapping WHERE pan_id = %s', (session['pan_id'],))
            mapping = cur.fetchone()
            if not mapping:
                 return render_template('category.html')

            person_id = mapping[0]
            cur.execute('SELECT 1 FROM businesses WHERE person_id = %s', (person_id,))
            business_user = cur.fetchone()
            if business_user:
                session['user_category'] = 'business'
                return redirect(url_for('dashboard_business'))

            cur.execute('SELECT 1 FROM job_person WHERE person_id = %s', (person_id,))
            job_user = cur.fetchone()
            if job_user:
                session['user_category'] = 'job'
                return redirect(url_for('dashboard_job'))

    return render_template('category.html')


@app.route('/select_category', methods=['POST'])
def select_category():
    data = request.get_json()
    category = data.get('category')
    session['user_category'] = category
    return jsonify({'success': True, 'redirect': url_for('details')})

# --- Main Details Form ---
@app.route('/details', methods=['GET', 'POST'])
def details():
    if 'pan_id' not in session:
        return redirect(url_for('signup'))

    if request.method == 'POST':
        category = session.get('user_category')
        pan_id = session.get('pan_id')

        with get_connection(autocommit=True) as conn:
            with conn.cursor(buffered=True) as cur:

                cur.execute("INSERT IGNORE INTO people_info (name, fathers_guardian_name, date_of_birth, gender, email, aadhar_number, mobile_number) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                               (request.form.get('name'), request.form.get('father'), request.form.get('dob'), request.form.get('gender'), request.form.get('email'), request.form.get('aadhar'), request.form.get('mno')))
                try:
                    cur.fetchall() # Only call if there are results (for DDL statements that might return info)
                except mysql.connector.InterfaceError:
                    pass # No result set to fetch
                
                cur.execute("SELECT id FROM people_info WHERE aadhar_number = %s", (request.form.get('aadhar'),))
                person = cur.fetchone()
                person_id = person[0] if person else None
                session['person_id'] = person_id

                if person_id:
                    cur.execute("INSERT IGNORE INTO user_pan_mapping (pan_id, person_id) VALUES (%s, %s)", (pan_id, person_id))
                    try:
                        cur.fetchall()
                    except mysql.connector.InterfaceError:
                        pass

                if category == "business":
                    cur.execute("DELETE FROM job_person WHERE person_id = %s", (person_id,))
                    try:
                        cur.fetchall()
                    except mysql.connector.InterfaceError:
                        pass
                    business_name = request.form.get('Bussname')
                    cur.execute("INSERT IGNORE INTO businesses (person_id, business_name) VALUES (%s, %s)", (person_id, business_name))
                    try:
                        cur.fetchall()
                    except mysql.connector.InterfaceError:
                        pass
                    cur.execute("SELECT id FROM businesses WHERE person_id = %s", (person_id,))
                    business = cur.fetchone()
                    if business:
                        session['business_id'] = business[0]
                    return redirect(url_for("business_details"))

                elif category == "job":
                    # Delete tax results first due to foreign key constraints
                    cur.execute("DELETE FROM tax_results_business WHERE person_id = %s", (person_id,))
                    try:
                        cur.fetchall()
                    except mysql.connector.InterfaceError:
                        pass
                    cur.execute("DELETE FROM businesses WHERE person_id = %s", (person_id,))
                    try:
                        cur.fetchall()
                    except mysql.connector.InterfaceError:
                        pass
                    cur.execute("INSERT IGNORE INTO job_person (person_id, employer_category, employer_tan_number) VALUES (%s, %s, %s)",
                                   (person_id, request.form.get('empc'), request.form.get('tan')))
                    try:
                        cur.fetchall()
                    except mysql.connector.InterfaceError:
                        pass
                    cur.execute("SELECT id FROM job_person WHERE person_id = %s", (person_id,))
                    job_person = cur.fetchone()
                    if job_person:
                        session['job_person_id'] = job_person[0]
                    return redirect(url_for("job_details"))

    return render_template('comm_det.html')

# ===================================================================
# --- Business User Workflow ---
# ===================================================================
@app.route('/business/details', methods=['GET', 'POST'])
def business_details():
    if request.method == 'POST':
        business_income = {
            'gross_income': get_float('gr-in'), 'other_income': get_float('oth-in'),
            'total_income': get_float('gr-in') + get_float('oth-in')
        }
        business_details = {
            'business_name': request.form.get('Bus'), 'product_name': request.form.get('pr-name'),
            'purchase_value': get_float('pur-price'), 'gst_rate_purchase': get_float('pur-gst'),
            'type_of_supply_purchase': request.form.get('tos-p'), 'sell_value': get_float('sal-price'),
            'gst_rate_sell': get_float('sell-gst'), 'type_of_supply_sell': request.form.get('tos-s')
        }

        # Store in session
        session['business_income'] = business_income
        session['business_details'] = business_details

        # Insert into database
        with get_connection(autocommit=True) as conn:
            with conn.cursor(buffered=True) as cur:
                # Insert business details
                cur.execute('''INSERT INTO business_details
                    (business_id, business_name, product_name, purchase_value, gst_rate_purchase,
                     type_of_supply_purchase, sell_value, gst_rate_sell, type_of_supply_sell)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (session.get('business_id'), business_details['business_name'], business_details['product_name'],
                     business_details['purchase_value'], str(business_details['gst_rate_purchase']),
                     business_details['type_of_supply_purchase'], business_details['sell_value'],
                     str(business_details['gst_rate_sell']), business_details['type_of_supply_sell']))
                try:
                    cur.fetchall()
                except mysql.connector.InterfaceError:
                    pass

                # Insert income details
                cur.execute('''INSERT INTO income_details
                    (business_id, gross_income, other_income, Total_revenue)
                    VALUES (%s, %s, %s, %s)''',
                    (session.get('business_id'), business_income['gross_income'],
                     business_income['other_income'], business_income['total_income']))
                try:
                    cur.fetchall()
                except mysql.connector.InterfaceError:
                    pass

        return redirect(url_for("business_expenses"))
    return render_template("buss_det.html")

@app.route('/business/expenses', methods=['GET', 'POST'])
def business_expenses():
    if request.method == 'POST':
        business_expenses = {
            'rent': get_float('rent'), 'employee_wage': get_float('emp-w'),
            'operating_expenses': get_float('op-exp'), 'subscription': get_float('sub'),
            'other_expenses': get_float('oth-expenses')
        }
        finance_deduction = {
            'section_80c': get_float('section-80c'), 'section_80d': get_float('section-80d'),
            'other_deduction': get_float('other-ded')
        }

        # Store in session
        session['business_expenses'] = business_expenses
        session['finance_deduction'] = finance_deduction

        # Insert into database
        with get_connection(autocommit=True) as conn:
            with conn.cursor(buffered=True) as cur:
                # Insert business expenses
                cur.execute('''INSERT INTO business_expenses
                    (business_id, rent, employee_wage, operating_expenses, subscription, other_expenses)
                    VALUES (%s, %s, %s, %s, %s, %s)''',
                    (session.get('business_id'), business_expenses['rent'], business_expenses['employee_wage'],
                     business_expenses['operating_expenses'], business_expenses['subscription'],
                     business_expenses['other_expenses']))
                try:
                    cur.fetchall()
                except mysql.connector.InterfaceError:
                    pass

        # Calculate tax here
        bus_income = session.get('business_income', {})
        bus_details = session.get('business_details', {})
        fin_deductions = session.get('finance_deduction', {})

        gross_revenue = bus_income.get('total_income', 0)
        total_expenses = sum(business_expenses.values())
        final_tax_payable, net_taxable_income = calc_bus_tax_new_regime(gross_revenue, total_expenses)

        gst_results = calculate_gst(
            bus_details.get('purchase_value', 0), int(bus_details.get('gst_rate_purchase', 0)),
            bus_details.get('type_of_supply_purchase', ''), bus_details.get('sell_value', 0),
            int(bus_details.get('gst_rate_sell', 0)), bus_details.get('type_of_supply_sell', '')
        )
        final_gst_payable = gst_results['net_payable']['total']

        insights = "AI insights available on results page."

        # Insert result
        with get_connection(autocommit=True) as conn:
            with conn.cursor(buffered=True) as cur:
                cur.execute('''INSERT INTO tax_results_business (person_id, pan_id, business_id, gross_income, net_taxable_income, gst_payable, final_tax_payable, insights)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (session.get('person_id'), session.get('pan_id'), session.get('business_id'), gross_revenue, net_taxable_income, final_gst_payable, final_tax_payable, insights))
                try:
                    cur.fetchall()
                except mysql.connector.InterfaceError:
                    pass

        # Store results in session
        session['business_results'] = {
            'gross_income': gross_revenue,
            'net_taxable_income': net_taxable_income,
            'gst_payable': final_gst_payable,
            'final_tax_payable': final_tax_payable,
            'total_expenses': total_expenses
        }

        return redirect(url_for("business_result"))
    return render_template("buss_deduct.html")

@app.route('/business/result')
def business_result():
    if 'business_results' not in session:
        flash("Session data is missing. Please restart the calculation.")
        return redirect(url_for('business_details'))

    results = session.get('business_results', {})
    fin_deductions = session.get('finance_deduction', {})

    insights = "Could not generate AI insights at this time."
    if GEMINI_API_KEY:
        try:
            prompt = f"Analyze this business data and provide 2-3 simple tax tips: Revenue ₹{results.get('gross_income', 0):,.2f}, Expenses ₹{results.get('total_expenses', 0):,.2f}, 80C Investment ₹{fin_deductions.get('section_80c', 0):,.2f}"
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            insights = response.text
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            insights = "Could not generate AI insights at this time."

    return render_template(
        "tax_result_bus.html",
        gross_income=round(results.get('gross_income', 0), 2),
        net_taxable_income=round(results.get('net_taxable_income', 0), 2),
        gst_payable=round(results.get('gst_payable', 0), 2),
        final_tax_payable=round(results.get('final_tax_payable', 0), 2),
        insights=insights
    )

# ===================================================================
# --- Job User Workflow ---
# ===================================================================
@app.route('/job/details', methods=['GET', 'POST'])
def job_details():
    if request.method == 'POST':
        job_income = {
            'financial_year': request.form.get('financial_year'), 'basic_salary': get_float('basic_salary'),
            'hra_received': get_float('hra_received'), 'savings_interest': get_float('savings_interest'),
            'fd_interest': get_float('fd_interest'), 'other_income': get_float('other_income')
        }

        # Store in session
        session['job_income'] = job_income

        # Insert into database
        with get_connection(autocommit=True) as conn:
            with conn.cursor(buffered=True) as cur:
                # Insert job details
                cur.execute('''INSERT INTO job_details
                    (person_id, financial_year, basic_salary, hra_received, interest_savings, interest_fd, other_income)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                    (session.get('job_person_id'), job_income['financial_year'], job_income['basic_salary'],
                     job_income['hra_received'], job_income['savings_interest'], job_income['fd_interest'],
                     job_income['other_income']))
                try:
                    cur.fetchall()
                except mysql.connector.InterfaceError:
                    pass

        return redirect(url_for("job_deductions"))
    return render_template("job_det.html")

@app.route('/job/deductions', methods=['GET', 'POST'])
def job_deductions():
    if request.method == 'POST':
        job_deductions = {
            'epf_ppf': get_float('epf_ppf'), 'life_ins': get_float('life_insurance'),
            'elss': get_float('elss'), 'home_loan_principal': get_float('home_loan_principal'),
            'tuition': get_float('tuition_fees'), 'other_80c': get_float('other_80c'),
            'health_ins_self': get_float('health_insurance_self'), 'health_ins_parents': get_float('health_insurance_parents'),
            'home_loan_interest': get_float('home_loan_interest'), 'education_loan_interest': get_float('education_loan_interest'),
            'donations': get_float('donations'), 'tds': get_float('tds')
        }

        # Store in session
        session['job_deductions'] = job_deductions

        # Insert into database
        with get_connection(autocommit=True) as conn:
            with conn.cursor(buffered=True) as cur:
                # Insert job deductions
                cur.execute('''INSERT INTO job_deductions
                    (person_id, section_80c_epf_ppf, section_80c_life_insurance, section_80c_elss_mutual_funds,
                     section_80c_home_loan_principal, section_80c_childrens_tuition, section_80c_other_investments,
                     section_80d_health_insurance_self_family, section_80d_health_insurance_parents,
                     section_24_home_loan_interest_paid, section_80e_education_loan_interest_paid,
                     section_80g_donations_charity, tds)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (session.get('job_person_id'), job_deductions['epf_ppf'], job_deductions['life_ins'],
                     job_deductions['elss'], job_deductions['home_loan_principal'], job_deductions['tuition'],
                     job_deductions['other_80c'], job_deductions['health_ins_self'], job_deductions['health_ins_parents'],
                     job_deductions['home_loan_interest'], job_deductions['education_loan_interest'],
                     job_deductions['donations'], job_deductions['tds']))
                try:
                    cur.fetchall()
                except mysql.connector.InterfaceError:
                    pass

        # Calculate tax here
        job_income = session.get('job_income', {})
        gross_income = sum(v for k, v in job_income.items() if k != 'financial_year')
        tds = job_deductions.get('tds', 0)
        final_tax_due, taxable_income = calc_job_tax_new_regime(gross_income, tds)

        insights = "AI insights available on results page."

        # Insert result
        with get_connection(autocommit=True) as conn:
            with conn.cursor(buffered=True) as cur:
                cur.execute('''
                    INSERT INTO tax_results_job (person_id, pan_id, financial_year, gross_income, tax, net_income, insights)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    session.get('person_id'), session.get('pan_id'), job_income.get('financial_year'),
                    gross_income, final_tax_due, taxable_income, insights
                ))
                try:
                    cur.fetchall()
                except mysql.connector.InterfaceError:
                    pass

        # Store results in session for display
        session['job_results'] = {
            'tax': final_tax_due,
            'net_income': taxable_income,
            'gross_income': gross_income,
            'insights': insights
        }

        return redirect(url_for("job_result"))
    return render_template("job_deduct.html")

@app.route('/job/result')
def job_result():
    if 'job_results' not in session:
        flash("Session data missing. Please restart the job calculation.")
        return redirect(url_for('job_details'))

    results = session.get('job_results', {})
    job_deductions = session.get('job_deductions', {})

    insights = "Could not generate AI insights at this time."
    if GEMINI_API_KEY:
        try:
            section_80c_total = sum(job_deductions.get(k, 0) for k in ['epf_ppf', 'life_ins', 'elss', 'home_loan_principal', 'tuition', 'other_80c'])
            health_insurance_80d = job_deductions.get('health_ins_self', 0) + job_deductions.get('health_ins_parents', 0)

            prompt = f"Analyze this salaried employee's data and give 2-3 tax tips: Gross Salary ₹{results.get('gross_income', 0):,.2f}, 80C Investments ₹{section_80c_total:,.2f}, 80D Health Insurance ₹{health_insurance_80d:,.2f}"
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            insights = response.text
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            insights = "Could not generate AI insights at this time."

    return render_template(
        "tax_result_job.html",
        tax=round(results.get('tax', 0), 2),
        net_income=round(results.get('net_income', 0), 2),
        gross_income=round(results.get('gross_income', 0), 2),
        insights=insights
    )

# ===================================================================
# --- Dashboard Routes (Corrected) ---
# ===================================================================
@app.route('/dashboard/business')
def dashboard_business():
    if 'pan_id' not in session:
        return redirect(url_for('signup'))

    pan_id = session.get('pan_id')
    with get_connection() as conn:
        with conn.cursor(buffered=True) as cur:
            cur.execute(
                '''SELECT id, gross_income, net_taxable_income, gst_payable, final_tax_payable, insights, created_at
                   FROM tax_results_business
                   WHERE pan_id = %s
                   ORDER BY created_at ASC''',
                (pan_id,)
            )
            results = cur.fetchall()
            column_names = [desc[0] for desc in cur.description]
            history = [dict(zip(column_names, row)) for row in results]

    history_for_template = history
    
    # FIX: Convert datetime objects to date strings for display and aggregation
    for row in history_for_template:
        if isinstance(row['created_at'], datetime.datetime):
            # Create a new field for the formatted date string
            row['created_at_display'] = row['created_at'].strftime('%Y-%m-%d')
        else:
             row['created_at_display'] = str(row['created_at']).split(' ')[0] # Fallback for safety

    # --- Aggregated yearly data (using the datetime object) ---
    from collections import defaultdict
    yearly_data = defaultdict(lambda: {'gross_income': [], 'gst_payable': [], 'final_tax_payable': []})
    for row in history_for_template:
        created_at_value = row['created_at']
        if isinstance(created_at_value, datetime.datetime):
            year = created_at_value.strftime('%Y')
        else:
            year = str(created_at_value)[:4]
            
        yearly_data[year]['gross_income'].append(row['gross_income'])
        yearly_data[year]['gst_payable'].append(row['gst_payable'])
        yearly_data[year]['final_tax_payable'].append(row['final_tax_payable'])

    sorted_years = sorted(yearly_data.keys())
    yearly_labels = sorted_years
    revenue_data_yearly = [sum(yearly_data[year]['gross_income']) for year in sorted_years]
    gst_data_yearly = [sum(yearly_data[year]['gst_payable']) for year in sorted_years]
    tax_data_yearly = [sum(yearly_data[year]['final_tax_payable']) for year in sorted_years]

    labels = [
        f"Calc {i+1} ({row['created_at'].strftime('%Y-%m-%d')})" 
        if isinstance(row['created_at'], datetime.datetime) 
        else f"Calc {i+1} ({str(row['created_at']).split(' ')[0]})"
        for i, row in enumerate(history_for_template)
    ]
    revenue_data = [float(row['gross_income'] or 0) for row in history_for_template]
    gst_data = [float(row['gst_payable'] or 0) for row in history_for_template]
    tax_data = [float(row['final_tax_payable'] or 0) for row in history_for_template]

    return render_template(
        'dash_bus.html',
        history=history_for_template,
        pan_number=pan_id,
        labels=labels,
        revenue_data=revenue_data,
        gst_data=gst_data,
        tax_data=tax_data,
        yearly_labels=yearly_labels,
        revenue_data_yearly=revenue_data_yearly,
        gst_data_yearly=gst_data_yearly,
        tax_data_yearly=tax_data_yearly
    )


@app.route('/dashboard/job')
def dashboard_job():
    if 'pan_id' not in session:
        return redirect(url_for('signup'))

    pan_id = session.get('pan_id')
    with get_connection() as conn:
        with conn.cursor(buffered=True) as cur:
            cur.execute('SELECT * FROM tax_results_job WHERE pan_id = %s ORDER BY created_at DESC', (pan_id,))
            results = cur.fetchall()
            column_names = [desc[0] for desc in cur.description]
            history = [dict(zip(column_names, row)) for row in results]

    history_for_template = history
    
    # FIX: Convert datetime objects in 'created_at' to date strings
    for row in history_for_template:
        if isinstance(row['created_at'], datetime.datetime):
            row['created_at_display'] = row['created_at'].strftime('%Y-%m-%d')
        else:
             row['created_at_display'] = str(row['created_at']).split(' ')[0] # Fallback for safety

    labels = [row['financial_year'] for row in reversed(history_for_template)]
    gross_income_data = [row['gross_income'] for row in reversed(history_for_template)]
    tax_data = [row['tax'] for row in reversed(history_for_template)]
    net_income_data = [row['net_income'] for row in reversed(history_for_template)]

    return render_template(
        'dash_job.html',
        history=history_for_template,
        pan_number=pan_id,
        total_calculations=len(history_for_template),
        labels=labels,
        gross_income_data=gross_income_data,
        tax_data=tax_data,
        net_income_data=net_income_data
    )

# ===================================================================
# --- PDF Download Routes ---
# ===================================================================
@app.route('/download-business-report')
def download_business_report():
    required_keys = ['person_id', 'business_income', 'business_details', 'business_expenses', 'finance_deduction']
    if not all(key in session for key in required_keys):
        flash("Session expired. Please fill out business forms again to download.")
        return redirect(url_for('business_details'))

    # Gather data from session
    bus_income = session.get('business_income', {})
    bus_details = session.get('business_details', {})
    bus_expenses = session.get('business_expenses', {})
    fin_deductions = session.get('finance_deduction', {})

    with get_connection() as conn:
        with conn.cursor(buffered=True) as cur:
            cur.execute("SELECT * FROM people_info WHERE id = %s", (session.get('person_id'),))
            person = cur.fetchone()
            personal = {
                'name': person[1] if person else 'N/A',
                'email': person[4] if person else 'N/A',
                'phone': person[6] if person else 'N/A',  # Changed from mobile_number to phone to match PDF template
                'age': 'N/A'  # Not stored, placeholder
            }

    # Prepare data for PDF
    data = {
        'personal': personal,
        'income': {
            'gross_income': bus_income.get('total_income', 0),
            'other_income': bus_income.get('other_income', 0),
            'total_revenue': bus_income.get('total_income', 0),
            'business_name': bus_details.get('business_name', ''),
            'product_name': bus_details.get('product_name', ''),
        },
        'gst': {
            'purchase_value': bus_details.get('purchase_value', 0),
            'purchase_rate': bus_details.get('gst_rate_purchase', 0),
            'purchase_supply_type': bus_details.get('type_of_supply_purchase', ''),
            'sell_value': bus_details.get('sell_value', 0),
            'sell_rate': bus_details.get('gst_rate_sell', 0),
            'sell_supply_type': bus_details.get('type_of_supply_sell', ''),
        },
        'expenses': {
            'rent': bus_expenses.get('rent', 0),
            'wages': bus_expenses.get('employee_wage', 0),
            'operating_expenses': bus_expenses.get('operating_expenses', 0),
            'subscription': bus_expenses.get('subscription', 0),
            'other': bus_expenses.get('other_expenses', 0),
            '80c': fin_deductions.get('section_80c', 0),
            '80d': fin_deductions.get('section_80d', 0),
            'other_deductions': fin_deductions.get('other_deduction', 0),
        },
        'summary': {
            'taxable_income': session.get('net_taxable_income', 0),  # From result
            'final_tax_due': session.get('final_tax_payable', 0),
        }
    }

    # Calculate tax values if not available in session (user might download PDF without going through result page)
    if not session.get('net_taxable_income') or not session.get('final_tax_payable'):
        gross_revenue = bus_income.get('total_income', 0)
        total_expenses = sum(bus_expenses.values())
        final_tax_payable, net_taxable_income = calc_bus_tax_new_regime(gross_revenue, total_expenses)
        data['summary']['taxable_income'] = net_taxable_income
        data['summary']['final_tax_due'] = final_tax_payable

    # Generate PDF
    buffer = create_business_report(data)

    # Return PDF
    return send_file(buffer, as_attachment=True, download_name='business_tax_report.pdf', mimetype='application/pdf')


@app.route('/download-job-report')
def download_job_report():
    required_keys = ['person_id', 'job_income', 'job_deductions']
    if not all(key in session for key in required_keys):
        flash("Session expired. Please fill out job forms again to download.")
        return redirect(url_for('job_details'))

    # Gather data from session
    job_income = session.get('job_income', {})
    job_deductions = session.get('job_deductions', {})

    # Get personal info
    with get_connection() as conn:
        with conn.cursor(buffered=True) as cur:
            cur.execute("SELECT * FROM people_info WHERE id = %s", (session.get('person_id'),))
            person = cur.fetchone()
            personal = {
                'name': person[1] if person else 'N/A',
                'email': person[4] if person else 'N/A',
                'mobile_number': person[6] if person else 'N/A',
            }

    # Calculate totals
    gross_income = sum(v for k, v in job_income.items() if k != 'financial_year')
    tds = job_deductions.get('tds', 0)
    final_tax_due, taxable_income = calc_job_tax_new_regime(gross_income, tds)

    # Prepare data for PDF
    data = {
        'personal': personal,
        'financial_year': job_income.get('financial_year', 'N/A'),
        'income': {
            'basic_salary': job_income.get('basic_salary', 0),
            'hra_received': job_income.get('hra_received', 0),
            'savings_interest': job_income.get('savings_interest', 0),
            'fd_interest': job_income.get('fd_interest', 0),
            'other_income': job_income.get('other_income', 0),
        },
        'summary': {
            'gross_income': gross_income,
            'standard_deduction': 50000,  # Assuming standard deduction
            'taxable_income': taxable_income,
            'total_tax': final_tax_due,
            'tds': tds,
            'final_tax_due': final_tax_due,
        }
    }
    # Generate PDF
    buffer = create_job_report(data)

    # Return PDF
    return send_file(buffer, as_attachment=True, download_name='job_tax_report.pdf', mimetype='application/pdf')

@app.route('/gst_rates', methods=['GET'])
def gst_rates():
    chapter_heading_data = request.args.get('data')

    if not chapter_heading_data:
        return jsonify({'error': 'Missing required parameter: data (chapter_heading)'})

    try:
        with get_connection() as conn:
            with conn.cursor(buffered=True, dictionary=True) as cur:
                query = 'SELECT * FROM gst_rates WHERE chapter_heading = %s'
                cur.execute(query, (chapter_heading_data,))
                results = cur.fetchall()
            
        if not results:
            return jsonify({
                'message': f"No GST data found for chapter_heading: {chapter_heading_data}"
            })
        
        return jsonify(results), 200

    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return jsonify({'error': 'Database operation failed', 'details': str(err)})
    except Exception as e:
        print(f"Unhandled Error: {e}")
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)})
    return render_template('gst_rates.html')



if __name__ == '__main__':
    app.run(debug=True)