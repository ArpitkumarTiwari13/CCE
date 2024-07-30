from flask import Flask, render_template, request, redirect, url_for
import pyodbc
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import csv
from io import StringIO
from flask import make_response
from flask import send_from_directory
import zipfile




#UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")

app = Flask(__name__, static_folder='static')
#app = Flask(__name__)

#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_FOLDER'] = 'static'

# SQL Server connection settings
server = 'Rishabh-123\\SQLEXPRESS'
database = 'agricce'
driver = '{ODBC Driver 17 for SQL Server}'
connection_string = f"""
DRIVER={driver};
SERVER={server};
DATABASE={database};
Trusted_Connection=yes;
"""
def handle_file_upload(file, table_name):
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None  # return None if no file


def safe_convert_to_float(value, default=0.0):
    try:
        return float(value)
    except ValueError:
        print(f"ValueError converting '{value}' to float. Using default value: {default}")
        return default


# Function to get a database connection
def get_db_connection():
    try:
        conn = pyodbc.connect(connection_string)
        return conn
    except pyodbc.Error as ex:
        print("Connection failed:", ex)
        return None

@app.route('/submit', methods=['GET', 'POST'])
def submit_data():
    if request.method == 'POST':
        form_data = request.form

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()

            layout_photo_path = handle_file_upload(request.files['layout_photo'], "layout_photo")
            biomass_photo_path = handle_file_upload(request.files['biomass_wt_photo'], "biomass_photo")
            gram_photo_path = handle_file_upload(request.files['gram_wt_photo'], "gram_photo")

            insert_query = '''
                       INSERT INTO cce_information (
                           layout_photo, district, tehsil, halka, crop_name, crop_variety, 
                           farmer_name, area_of_field, irrigation_type, cce_date, biomass_wt, 
                           biomass_photo, biomass_moisture, gram_wt, gram_photo, gram_moisture,
                           latitude, longitude,remarks
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       '''

            cursor.execute(insert_query, (
                 layout_photo_path, form_data['district'],
                form_data['tehsil'], form_data['halka'], form_data['crop_name'], form_data['crop_variety'],
                form_data['farmer_name'], safe_convert_to_float(form_data.get('area_of_field', 0.0)),
                int(form_data.get('irrigation_type', 0)), datetime.strptime(form_data['cce_date'], '%Y-%m-%d').date(),
                safe_convert_to_float(form_data.get('biomass_wt', 0.0)), biomass_photo_path,
                safe_convert_to_float(form_data.get('biomass_moisture', 0.0)),
                safe_convert_to_float(form_data.get('gram_wt', 0.0)),
                gram_photo_path, safe_convert_to_float(form_data.get('gram_moisture', 0.0)),safe_convert_to_float(form_data.get('latitude', 0.0)),
                safe_convert_to_float(form_data.get('longitude', 0.0)), form_data['remarks']
            ))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('index'))
        else:
            return "Database connection failed", 500

    return render_template('submit_form.html')


@app.route('/view_data')
def view_data():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        select_query = '''SELECT * FROM cce_information'''
        cursor.execute(select_query)
        data = cursor.fetchall()
        header = [desc[0] for desc in cursor.description]  # Get header info here
        cursor.close()
        conn.close()
        return render_template('view_data.html', data=data, header=header)
    else:
        return "Database connection failed", 500


@app.route('/download_data')
def download_data():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        select_query = '''SELECT * FROM cce_information'''
        cursor.execute(select_query)

        # Retrieve header information before closing the cursor
        header = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        cursor.close()
        conn.close()

        # Create a CSV file in memory
        output = StringIO()
        writer = csv.writer(output)

        # Write the header
        writer.writerow(header)

        # Write the data
        for row in data:
            writer.writerow(row)

        output.seek(0)

        # Create a response with the CSV data
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=cce_information.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response
    else:
        return "Database connection failed", 500


@app.route('/upload_kml', methods=['POST'])
def upload_kml():
    file = request.files['kml_file']
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        if filename.endswith('.kmz'):
            # Handle KMZ files
            with zipfile.ZipFile(file, 'r') as kmz:
                # Extract all files
                kmz.extractall(app.config['UPLOAD_FOLDER'])
                # Find KML file
                kml_files = [f for f in kmz.namelist() if f.endswith('.kml')]
                if kml_files:
                    kml_filename = kml_files[0]
                    # Save the KML file
                    kml_filepath = os.path.join(app.config['UPLOAD_FOLDER'], kml_filename)
                    os.rename(os.path.join(app.config['UPLOAD_FOLDER'], kml_filename), kml_filepath)
                    return redirect(url_for('show_kml', filename=kml_filename))
                else:
                    return "No KML file found in KMZ", 400
        elif filename.endswith('.kml'):
            # Handle KML files directly
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return redirect(url_for('show_kml', filename=filename))
        else:
            return "Invalid file type", 400
    return "No file uploaded", 400


@app.route('/show_kml/<filename>')
def show_kml(filename):
    kml_file_url = url_for('static', filename=filename)
    return render_template('upload_kml.html', kml_file=kml_file_url)


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/upload_kml', methods=['GET'])
def upload_kml_form():
    return render_template('upload_kml.html')

# Homepage route
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0')
