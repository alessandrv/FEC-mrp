from flask import Flask, jsonify
import pyodbc
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Define your connection string
connection_string = 'DSN=fec;UID=informix;PWD=informix;'

# Function to establish a database connection
def connect_to_db():
    try:
        return pyodbc.connect(connection_string)
    except pyodbc.Error as e:
        raise Exception(f"Unable to connect to the database: {str(e)}")

# Route to generate the MRP report
@app.route('/report', methods=['GET'])
def generate_report():
    conn = connect_to_db()  # Connect to the database
    cursor = conn.cursor()

    # SQL query for the report
    query = '''
    SELECT amg_code, amg_dest, amp_lead AS lt, 
           COALESCE((SELECT ROUND(dep_scom) FROM mgdepo WHERE dep_arti = amg_code AND dep_code = 1), 0) AS scrt,
           -- Additional fields for stock levels, orders, etc.
           (SELECT ROUND(dep_qgiai + dep_qcar - dep_qsca, 0) FROM mgdepo WHERE dep_arti = amg_code AND dep_code = 1) AS giac_d01,
           CASE 
               WHEN (SELECT ROUND(dep_qgiai + dep_qcar - dep_qsca, 0) FROM mgdepo WHERE dep_arti = amg_code AND dep_code = 1) < COALESCE((SELECT ROUND(dep_scom) FROM mgdepo WHERE dep_arti = amg_code AND dep_code = 1), 0)
               THEN 'Below Minimum Stock'
               ELSE 'Stock OK'
           END AS stock_status,
           DATEADD(DAY, amp_lead, CURRENT_DATE) AS restock_date
    FROM mganag
    WHERE amg_stat = 'D' AND COALESCE(amg_fagi, 'S') = 'S'
    '''

    cursor.execute(query)
    rows = cursor.fetchall()

    # Convert the result into a list of dictionaries
    report_data = []
    columns = [column[0] for column in cursor.description]  # Get column names
    for row in rows:
        report_data.append(dict(zip(columns, row)))

    cursor.close()
    conn.close()

    return jsonify(report_data)

if __name__ == '__main__':
    app.run(debug=True)
