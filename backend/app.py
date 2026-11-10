from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

app = Flask(__name__)
CORS(app)


# MySQL Database Connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="itum_medical_center",
        port=3306
    )


# Home Route
@app.route("/")
def home():
    return jsonify({
        "message": "ITUM Medical Center Backend is running!"
    })


# Database Test
@app.route("/db-test")
def db_test():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        result = cursor.fetchone()

        cursor.close()
        connection.close()

        return jsonify({
            "message": "MySQL Database Connected Successfully!",
            "user_count": result[0]
        })

    except mysql.connector.Error as error:
        return jsonify({"error": str(error)}), 500


# User Registration
@app.route("/register", methods=["POST"])
def register():

    data = request.get_json(silent=True) or {}

    full_name = data.get("full_name", "").strip()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    patient_type = data.get("patient_type", "").strip().lower()
    registration_number = data.get("registration_number", "").strip()

    if not all([full_name, username, email, password,
                patient_type, registration_number]):
        return jsonify({
            "error": "All required fields must be filled."
        }), 400

    if patient_type not in ["student", "staff"]:
        return jsonify({
            "error": "Only Students and Staff can register."
        }), 400

    if len(password) < 8:
        return jsonify({
            "error": "Password must contain at least 8 characters."
        }), 400

    password_hash = generate_password_hash(password)

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO users
            (full_name, username, email, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (full_name, username, email, password_hash, patient_type)
        )

        user_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO patients
            (user_id, patient_type, registration_number)
            VALUES (%s, %s, %s)
            """,
            (user_id, patient_type, registration_number)
        )

        connection.commit()

        return jsonify({
            "message": "Registration successful!"
        }), 201

    except mysql.connector.IntegrityError:
        if connection:
            connection.rollback()

        return jsonify({
            "error": "Username, email or registration number already exists."
        }), 409

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()

        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# User Login
@app.route("/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({
            "error": "Username and password are required."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT user_id, full_name, username,
                   password_hash, role
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

        user = cursor.fetchone()

        if user and check_password_hash(
            user["password_hash"], password
        ):
            return jsonify({
                "message": "Login successful!",
                "user": {
                    "user_id": user["user_id"],
                    "full_name": user["full_name"],
                    "username": user["username"],
                    "role": user["role"]
                }
            }), 200

        return jsonify({
            "error": "Invalid username or password."
        }), 401

    except mysql.connector.Error as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

      # Get All Doctors
@app.route("/doctors", methods=["GET"])
def get_doctors():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                d.doctor_id,
                u.full_name,
                d.specialization
            FROM doctors d
            JOIN users u ON d.user_id = u.user_id
            ORDER BY u.full_name
        """)

        doctors = cursor.fetchall()

        return jsonify({
            "doctors": doctors
        }), 200

    except mysql.connector.Error as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()    

            
# Book Appointment
@app.route("/appointments", methods=["POST"])
def book_appointment():

    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    doctor_id = data.get("doctor_id")
    appointment_date = data.get("appointment_date", "")
    appointment_time = data.get("appointment_time", "")
    reason = data.get("reason", "").strip()

    if not all([user_id, doctor_id, appointment_date,
                appointment_time, reason]):
        return jsonify({
            "error": "Please fill in all appointment details."
        }), 400

    try:
        user_id = int(user_id)
        doctor_id = int(doctor_id)
        selected_date = date.fromisoformat(appointment_date)

        if selected_date < date.today():
            return jsonify({
                "error": "Appointment date cannot be in the past."
            }), 400

    except (ValueError, TypeError):
        return jsonify({
            "error": "Invalid user, doctor or appointment date."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check whether the user is a registered patient
        cursor.execute("""
            SELECT patient_id
            FROM patients
            WHERE user_id = %s
        """, (user_id,))

        patient = cursor.fetchone()

        if not patient:
            return jsonify({
                "error": "Patient account not found."
            }), 404

        # Check whether the selected doctor exists
        cursor.execute("""
            SELECT doctor_id
            FROM doctors
            WHERE doctor_id = %s
        """, (doctor_id,))

        doctor = cursor.fetchone()

        if not doctor:
            return jsonify({
                "error": "Selected doctor not found."
            }), 404

        # Save appointment
        cursor.execute("""
            INSERT INTO appointments
            (patient_id, doctor_id, appointment_date,
             appointment_time, reason, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
        """, (
            patient["patient_id"],
            doctor_id,
            appointment_date,
            appointment_time,
            reason
        ))

        appointment_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "message": "Appointment request submitted successfully!",
            "appointment_id": appointment_id,
            "status": "pending"
        }), 201

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()

        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

     
# Get Student/Staff Appointments
@app.route("/student/appointments/<int:user_id>", methods=["GET"])
def get_student_appointments(user_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check whether the user is a registered patient
        cursor.execute("""
            SELECT patient_id
            FROM patients
            WHERE user_id = %s
        """, (user_id,))

        patient = cursor.fetchone()

        if not patient:
            return jsonify({
                "error": "Patient account not found."
            }), 404

        # Get appointments booked by this patient
        cursor.execute("""
            SELECT
                a.appointment_id,
                a.appointment_date,
                a.appointment_time,
                a.reason,
                a.status,
                u.full_name AS doctor_name,
                d.specialization
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.doctor_id
            JOIN users u ON d.user_id = u.user_id
            WHERE a.patient_id = %s
            ORDER BY a.appointment_date DESC,
                     a.appointment_time DESC
        """, (patient["patient_id"],))

        appointments = cursor.fetchall()

        for appointment in appointments:
            appointment["appointment_date"] = str(
                appointment["appointment_date"]
            )
            appointment["appointment_time"] = str(
                appointment["appointment_time"]
            )

        return jsonify({
            "appointments": appointments
        }), 200

    except mysql.connector.Error as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
       
  
@app.route("/doctor/appointments/<int:user_id>", methods=["GET"])
def get_doctor_appointments(user_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check whether the user is a doctor
        cursor.execute("""
            SELECT doctor_id
            FROM doctors
            WHERE user_id = %s
        """, (user_id,))

        doctor = cursor.fetchone()

        if not doctor:
            return jsonify({"error": "Doctor account not found."}), 404

        # Get appointments assigned to this doctor
        cursor.execute("""
            SELECT
                a.appointment_id,
                u.full_name AS student_name,
                p.registration_number,
                a.appointment_date,
                a.appointment_time,
                a.reason,
                a.status
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN users u ON p.user_id = u.user_id
            WHERE a.doctor_id = %s
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """, (doctor["doctor_id"],))

        appointments = cursor.fetchall()

        for appointment in appointments:
            appointment["appointment_date"] = str(
                appointment["appointment_date"]
            )
            appointment["appointment_time"] = str(
                appointment["appointment_time"]
            )

        return jsonify({"appointments": appointments}), 200

    except mysql.connector.Error as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

@app.route("/appointments/<int:appointment_id>/status", methods=["PUT"])
def update_appointment_status(appointment_id): 

    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip().lower()
    user_id = data.get("user_id")

    if new_status not in ["approved", "rejected"]:
        return jsonify({"error": "Invalid appointment status."}), 400

    if not user_id:
        return jsonify({"error": "Doctor user ID is required."}), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Verify doctor account
        cursor.execute("""
            SELECT doctor_id
            FROM doctors
            WHERE user_id = %s
        """, (user_id,))

        doctor = cursor.fetchone()

        if not doctor:
            return jsonify({"error": "Doctor account not found."}), 403

        # Check appointment belongs to this doctor
        cursor.execute("""
            SELECT status
            FROM appointments
            WHERE appointment_id = %s
            AND doctor_id = %s
        """, (appointment_id, doctor["doctor_id"]))

        appointment = cursor.fetchone()

        if not appointment:
            return jsonify({"error": "Appointment not found."}), 404

        if appointment["status"] != "pending":
            return jsonify({
                "error": "Only pending appointments can be reviewed."
            }), 400

        # Update appointment status
        cursor.execute("""
            UPDATE appointments
            SET status = %s
            WHERE appointment_id = %s
            AND doctor_id = %s
        """, (new_status, appointment_id, doctor["doctor_id"]))

        connection.commit()

        return jsonify({
            "message": "Appointment " + new_status + " successfully!",
            "status": new_status
        }), 200

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()

        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()      

        # Create Medical Record
@app.route("/medical-records", methods=["POST"])
def create_medical_record():

    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    patient_id = data.get("patient_id")
    diagnosis = data.get("diagnosis", "").strip()
    treatment = data.get("treatment", "").strip()

    if not all([user_id, patient_id, diagnosis, treatment]):
        return jsonify({
            "error": "All medical record details are required."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Verify doctor
        cursor.execute("""
            SELECT doctor_id
            FROM doctors
            WHERE user_id = %s
        """, (user_id,))

        doctor = cursor.fetchone()

        if not doctor:
            return jsonify({
                "error": "Doctor account not found."
            }), 403

        # Verify patient
        cursor.execute("""
            SELECT patient_id
            FROM patients
            WHERE patient_id = %s
        """, (patient_id,))

        patient = cursor.fetchone()

        if not patient:
            return jsonify({
                "error": "Patient not found."
            }), 404

        # Save medical record
        cursor.execute("""
            INSERT INTO medical_records
            (patient_id, doctor_id, diagnosis, treatment, record_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            patient_id,
            doctor["doctor_id"],
            diagnosis,
            treatment,
            date.today()
        ))

        connection.commit()

        return jsonify({
            "message": "Medical record created successfully!"
        }), 201

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()

        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()   

            # Get All Patients for Doctor
@app.route("/patients", methods=["GET"])
def get_all_patients():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                p.patient_id,
                u.full_name,
                p.registration_number,
                p.patient_type
            FROM patients p
            JOIN users u ON p.user_id = u.user_id
            ORDER BY u.full_name
        """)

        patients = cursor.fetchall()

        return jsonify({
            "patients": patients
        }), 200

    except mysql.connector.Error as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close() 

# Get Student/Staff Medical Records
@app.route("/student/medical-records/<int:user_id>", methods=["GET"])
def get_student_medical_records(user_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT patient_id
            FROM patients
            WHERE user_id = %s
        """, (user_id,))

        patient = cursor.fetchone()

        if not patient:
            return jsonify({
                "error": "Patient account not found."
            }), 404

        cursor.execute("""
            SELECT
                mr.record_id,
                mr.diagnosis,
                mr.treatment,
                mr.record_date,
                u.full_name AS doctor_name
            FROM medical_records mr
            JOIN doctors d ON mr.doctor_id = d.doctor_id
            JOIN users u ON d.user_id = u.user_id
            WHERE mr.patient_id = %s
            ORDER BY mr.record_date DESC
        """, (patient["patient_id"],))

        records = cursor.fetchall()

        for record in records:
            record["record_date"] = str(record["record_date"])

        return jsonify({
            "medical_records": records
        }), 200

    except mysql.connector.Error as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    app.run(debug=True, port=5000)