import os
import mysql.connector
from mysql.connector.cursor import MySQLCursorBuffered
from dotenv import load_dotenv
from contextlib import contextmanager

# Load environment variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# --- Connection Details from Environment Variables ---
TIDB_HOST = os.getenv("TIDB_HOST")
TIDB_NAME = os.getenv("TIDB_NAME") # e.g., 'test'
TIDB_USER = os.getenv("TIDB_USER")
TIDB_PASS = os.getenv("TIDB_PASS")
# TIDB_SSL_CA = os.getenv("TIDB_SSL_CA")
TIDB_PORT = int(os.getenv("TIDB_PORT", 4000))
# ---------------------------------------------------

def create_app_database(db_name):
    """Connects to TiDB without a default DB to ensure the application DB exists."""
    conn = None
    try:
        # 1. Connect without specifying the target database
        conn = mysql.connector.connect(
            host=TIDB_HOST,
            port=TIDB_PORT,
            user=TIDB_USER,
            password=TIDB_PASS,

            connection_timeout=10
        )
        # Use a non-buffered cursor since DDL/DML does not return many rows
        cursor = conn.cursor()
        
        # 2. Execute CREATE DATABASE IF NOT EXISTS
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
        conn.commit()
        print(f"Ensured database '{db_name}' exists.")
        
    except mysql.connector.Error as err:
        print(f"Failed to create/ensure database '{db_name}': {err}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return True


def get_db_connection():
    """Establishes and returns a raw connection to the TiDB Cloud database, including the DB name."""
    try:
        conn = mysql.connector.connect(
            host=TIDB_HOST,
            port=TIDB_PORT,
            user=TIDB_USER,
            password=TIDB_PASS,
            database=TIDB_NAME, # <--- Now guaranteed to exist
            # ssl_ca=TIDB_SSL_CA,
            connection_timeout=10
        )
        return conn
    except mysql.connector.Error as err:
        print(f"TiDB Cloud connection failed: {err}")
        return None 


@contextmanager
def get_connection(autocommit=False):
    """Context manager for the TiDB connection, using buffered cursor for SELECTs."""
    if not create_app_database(TIDB_NAME):
        raise ConnectionError(f"Critical failure: Cannot confirm existence of database {TIDB_NAME}.")
        
    conn = get_db_connection()
    if conn is None:
        raise ConnectionError("Failed to establish TiDB connection to target DB.")
    
    conn.autocommit = autocommit

    try:
        # use buffered cursor
        cursor = conn.cursor(buffered=True)
        yield conn
        if not autocommit:
            conn.commit()
    except Exception as e:
        if not autocommit:
            conn.rollback()
        raise e
    finally:
        if conn and conn.is_connected():
            conn.close()



# NOTE: Removed execute_schema_change wrapper function to simplify DDL execution.

def init_db():
    """Connects to TiDB Cloud and creates the necessary tables."""
    try:
        # We use autocommit=False to force an explicit commit at the end, guaranteeing DDL execution.
        with get_connection(autocommit=False) as conn:
            # Use a standard, non-buffered cursor for initialization DDL, which allows us to control fetchall().
            # NOTE: We use conn.cursor() here instead of conn.cursor(buffered=True) for fine-grained control.
            cursor = conn.cursor() 
            print(f"Successfully connected to TiDB Cloud and set target DB: {TIDB_NAME}.")

            # --- DDL Execution Helper ---
            def execute_ddl(cur, statement):
                cur.execute(statement)
                try:
                    # Crucial: DDL statements often yield a result set that must be fetched.
                    cur.fetchall() 
                except Exception:
                    pass
            # ---------------------------

            # --- Drop Tables ---
# --- Drop Tables (in dependency-safe order) ---
            execute_ddl(cursor, "DROP TABLE IF EXISTS tax_results_job;")
            execute_ddl(cursor, "DROP TABLE IF EXISTS tax_results_business;")
            execute_ddl(cursor, "DROP TABLE IF EXISTS job_deductions;")
            execute_ddl(cursor, "DROP TABLE IF EXISTS job_details;")
            execute_ddl(cursor, "DROP TABLE IF EXISTS business_expenses;")
            execute_ddl(cursor, "DROP TABLE IF EXISTS business_details;")
            execute_ddl(cursor, "DROP TABLE IF EXISTS income_details;")
            execute_ddl(cursor, "DROP TABLE IF EXISTS job_person;")
            execute_ddl(cursor, "DROP TABLE IF EXISTS businesses;")
            execute_ddl(cursor, "DROP TABLE IF EXISTS user_pan_mapping;")
            execute_ddl(cursor, "DROP TABLE IF EXISTS people_info;")
            execute_ddl(cursor, "DROP TABLE IF EXISTS user;")

            
            # --- Table Creation ---
            # User Table
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS user (
                id INT PRIMARY KEY AUTO_INCREMENT,
                pan_id VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )''')
            # People Info Table
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS people_info (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255), 
                fathers_guardian_name VARCHAR(255), 
                date_of_birth DATE,
                gender VARCHAR(50), 
                email VARCHAR(255), 
                aadhar_number VARCHAR(12) UNIQUE, 
                mobile_number VARCHAR(10)
            )''')
            # User PAN Mapping
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS user_pan_mapping (
                pan_id VARCHAR(50) PRIMARY KEY,
                person_id INT,
                FOREIGN KEY (person_id) REFERENCES people_info(id)
            )''')
            # Business Tables
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS businesses (
                id INT PRIMARY KEY AUTO_INCREMENT,
                person_id INT,
                business_name VARCHAR(255),
                date_of_gst_registration DATE,
                gstin VARCHAR(20),
                nature_of_business VARCHAR(255),
                FOREIGN KEY(person_id) REFERENCES people_info(id)
            )''')
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS gst_rates (
                serial_no INT PRIMARY KEY AUTO_INCREMENT,
                chapter_heading VARCHAR(50),
                description TEXT,
                cgst_rate DECIMAL(5,2),
                sgst_rate DECIMAL(5,2),
                igst_rate DECIMAL(5,2)
             )''')
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS income_details (
                detail_id INTEGER PRIMARY KEY AUTO_INCREMENT,
                business_id INTEGER,
                gross_income REAL,
                other_income REAL,
                Total_revenue REAL,
                FOREIGN KEY(business_id) REFERENCES businesses(id)
            )''')
            execute_ddl(cursor, '''
            CREATE TABLE business_details (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                business_id INTEGER,
                business_name TEXT,
                product_name TEXT,
                purchase_value REAL,
                gst_rate_purchase TEXT,
                type_of_supply_purchase TEXT,
                sell_value REAL,
                gst_rate_sell TEXT,
                type_of_supply_sell TEXT,
                FOREIGN KEY(business_id) REFERENCES businesses(id)
            )''')
            # Job Tables
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS business_expenses (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                business_id INTEGER,
                rent REAL,
                employee_wage REAL,
                operating_expenses REAL,
                subscription REAL,
                other_expenses REAL
            )''')
            # Tax Results History Tables (Job)
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS job_person (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                person_id INTEGER,
                employer_category TEXT,
                employer_tan_number TEXT,
                FOREIGN KEY(person_id) REFERENCES people_info(id)
            )''')
            # Tax Results History Tables (Business)
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS job_details (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                person_id INTEGER,
                financial_year TEXT,
                basic_salary REAL,
                hra_received REAL,
                interest_savings REAL,
                interest_fd REAL,
                other_income REAL,
                FOREIGN KEY(person_id) REFERENCES job_person(id)

            )''')
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS job_deductions (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                person_id INTEGER,
                section_80c_epf_ppf REAL,
                section_80c_life_insurance REAL,
                section_80c_elss_mutual_funds REAL,
                section_80c_home_loan_principal REAL,
                section_80c_childrens_tuition REAL,
                section_80c_other_investments REAL,
                section_80d_health_insurance_self_family REAL,
                section_80d_health_insurance_parents REAL,
                section_24_home_loan_interest_paid REAL,
                section_80e_education_loan_interest_paid REAL,
                section_80g_donations_charity REAL,
                tds REAL,
                FOREIGN KEY(person_id) REFERENCES job_person(id)

            )''')
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS tax_results_business (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                person_id INTEGER,
                pan_id VARCHAR(50),
                business_id INTEGER,
                gross_income REAL,
                net_taxable_income REAL,
                gst_payable REAL,
                final_tax_payable REAL,
                insights TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(person_id) REFERENCES people_info(id),
                FOREIGN KEY(business_id) REFERENCES businesses(id)
            )''')
            execute_ddl(cursor, '''
            CREATE TABLE IF NOT EXISTS tax_results_job (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                person_id INTEGER,
                pan_id VARCHAR(50),
                financial_year VARCHAR(20),
                gross_income REAL,
                tax REAL,
                net_income REAL,
                insights TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(person_id) REFERENCES people_info(id)

            )''')

            # The context manager will call conn.commit() when exiting the 'with' block.
            print("All tables created/recreated successfully.")

    except ConnectionError:
        print("Database initialization failed due to connection error.")
    except Exception as e:
        print(f"Database creation failed: {e}")

if __name__ == "__main__":
    init_db()
