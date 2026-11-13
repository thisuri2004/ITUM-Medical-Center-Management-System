from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Medical Certificate Upload Settings

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "uploads"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Maximum upload size: 50 MB
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

# Student Profile Picture Upload Settings

PROFILE_PICTURE_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "profile_pictures"
)

os.makedirs(PROFILE_PICTURE_FOLDER, exist_ok=True)

ALLOWED_PROFILE_EXTENSIONS = {"jpg", "jpeg", "png"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


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

@app.route("/student/profile/<int:user_id>", methods=["GET"])
def get_student_profile(user_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                u.user_id,
                u.full_name,
                u.username,
                u.email,
                u.role,
                p.patient_type,
                p.registration_number,
                p.division,
                p.contact_number
            FROM users u
            LEFT JOIN patients p
                ON u.user_id = p.user_id
            WHERE u.user_id = %s
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "error": "Student profile not found."
            }), 404

        return jsonify({
            "profile": user
        }), 200

    except mysql.connector.Error as error:
        return jsonify({
            "error": str(error)
        }), 500

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
            SELECT status, patient_id
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

        # Get student user ID
        cursor.execute("""
            SELECT user_id
            FROM patients
            WHERE patient_id = %s
        """, (appointment["patient_id"],))

        patient = cursor.fetchone()

        if not patient:
            connection.rollback()
            return jsonify({"error": "Patient not found."}), 404

        # Create notification
        title = "Appointment " + new_status.capitalize()

        message = (
            "Your appointment has been "
            + new_status
            + " by the doctor."
        )

        cursor.execute("""
            INSERT INTO notifications
            (user_id, title, message, notification_type, is_read)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            patient["user_id"],
            title,
            message,
            "appointment",
            0
        ))

        connection.commit()

        return jsonify({
            "message": "Appointment " + new_status + " successfully!",
            "status": new_status,
            "notification": "Notification created successfully."
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
    medicine_name = data.get("medicine_name", "").strip()
    dosage = data.get("dosage", "").strip()
    frequency = data.get("frequency", "").strip()
    duration = data.get("duration", "").strip()
    instructions = data.get("instructions", "").strip()

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
        # Get the newly created medical record ID
        record_id = cursor.lastrowid

        # Save prescription if medicine name is provided
        if medicine_name:

            cursor.execute("""
                INSERT INTO prescriptions
                (record_id, medicine_name, dosage, frequency,
                 duration, instructions)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                record_id,
                medicine_name,
                dosage,
                frequency,
                duration,
                instructions
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
                u.full_name AS doctor_name,
                p.medicine_name,
                p.dosage,
                p.frequency,
                p.duration,
                p.instructions
            FROM medical_records mr
            JOIN doctors d ON mr.doctor_id = d.doctor_id
            JOIN users u ON d.user_id = u.user_id
            LEFT JOIN prescriptions p ON mr.record_id = p.record_id
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

            # Submit Medical Certificate
@app.route("/medical-submissions", methods=["POST"])
def submit_medical_certificate():

    user_id = request.form.get("user_id")
    leave_from = request.form.get("leave_from")
    leave_to = request.form.get("leave_to")
    reason = request.form.get("reason", "").strip()

    medical_document = request.files.get("medical_document")

    # Check required details
    if not all([user_id, leave_from, leave_to, reason, medical_document]):
        return jsonify({
            "error": "All medical submission details are required."
        }), 400

    # Validate user ID
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user ID."}), 400

    # Validate dates
    try:
        from_date = date.fromisoformat(leave_from)
        to_date = date.fromisoformat(leave_to)

        if to_date < from_date:
            return jsonify({
                "error": "Leave To date cannot be before Leave From date."
            }), 400

    except ValueError:
        return jsonify({"error": "Invalid leave dates."}), 400

    # Check file
    if not medical_document.filename:
        return jsonify({"error": "Please select a file."}), 400

    if not allowed_file(medical_document.filename):
        return jsonify({
            "error": "Only PDF, JPG, JPEG and PNG files are allowed."
        }), 400

    connection = None
    saved_file_path = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check student/staff and get patient ID
        cursor.execute("""
            SELECT p.patient_id
            FROM patients p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id = %s
            AND u.role IN ('student', 'staff')
        """, (user_id,))

        patient = cursor.fetchone()

        if not patient:
            return jsonify({
                "error": "Student or staff account not found."
            }), 404

        patient_id = patient["patient_id"]

        # Generate safe unique filename
        original_filename = secure_filename(
            medical_document.filename
        )

        extension = original_filename.rsplit(".", 1)[1].lower()

        unique_filename = f"{uuid.uuid4().hex}.{extension}"

        saved_file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            unique_filename
        )

        # Save uploaded document
        medical_document.save(saved_file_path)

        # Store relative file path in database
        database_file_path = os.path.join(
            "uploads",
            unique_filename
        ).replace("\\", "/")

        # Insert submission
        cursor.execute("""
            INSERT INTO medical_submissions
            (
                patient_id,
                doctor_id,
                leave_from,
                leave_to,
                reason,
                medical_document,
                status
            )
            VALUES (%s, NULL, %s, %s, %s, %s, 'pending')
        """, (
            patient_id,
            leave_from,
            leave_to,
            reason,
            database_file_path
        ))

        connection.commit()

        return jsonify({
            "message": "Medical certificate submitted successfully.",
            "submission_id": cursor.lastrowid
        }), 201

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        if saved_file_path and os.path.exists(saved_file_path):
            os.remove(saved_file_path)

        print("Database Error:", error)

        return jsonify({
            "error": "Database error occurred."
        }), 500

    except Exception as error:

        if connection:
            connection.rollback()

        if saved_file_path and os.path.exists(saved_file_path):
            os.remove(saved_file_path)

        print("Submission Error:", error)

        return jsonify({
            "error": "Unable to submit medical certificate."
        }), 500

    finally:
        if connection:
            cursor.close()
            connection.close()


# Handle files exceeding 50 MB
@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "File is too large. Maximum allowed size is 50 MB."
    }), 413

    # Get Medical Certificate Submissions for Doctor
@app.route("/doctor/medical-submissions/<int:user_id>", methods=["GET"])
def get_doctor_medical_submissions(user_id):

    connection = None

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
            return jsonify({
                "error": "Doctor account not found."
            }), 404

        # Get medical submissions
        cursor.execute("""
            SELECT
                ms.submission_id,
                ms.patient_id,
                ms.leave_from,
                ms.leave_to,
                ms.reason,
                ms.medical_document,
                ms.status,
                ms.doctor_remarks,
                ms.submitted_at,
                u.full_name AS student_name,
                p.registration_number,
                p.patient_type

            FROM medical_submissions ms

            JOIN patients p
                ON ms.patient_id = p.patient_id

            JOIN users u
                ON p.user_id = u.user_id

            ORDER BY ms.submitted_at DESC
        """)

        submissions = cursor.fetchall()

        for submission in submissions:
            if submission["leave_from"]:
                submission["leave_from"] = str(
                    submission["leave_from"]
                )

            if submission["leave_to"]:
                submission["leave_to"] = str(
                    submission["leave_to"]
                )

            if submission["submitted_at"]:
                submission["submitted_at"] = str(
                    submission["submitted_at"]
                )

        return jsonify({
            "submissions": submissions
        }), 200

    except mysql.connector.Error as error:

        print("Database Error:", error)

        return jsonify({
            "error": "Unable to load medical submissions."
        }), 500

    finally:
        if connection:
            cursor.close()
            connection.close()

            # View Uploaded Medical Certificate
@app.route("/doctor/medical-submissions/<int:submission_id>/document", methods=["GET"])
def view_medical_certificate(submission_id):

    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"error": "Doctor user ID is required."}), 400

    connection = None

    try:
        user_id = int(user_id)

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
            return jsonify({"error": "Doctor account not found."}), 403

        # Find submitted document
        cursor.execute("""
            SELECT medical_document
            FROM medical_submissions
            WHERE submission_id = %s
        """, (submission_id,))

        submission = cursor.fetchone()

        if not submission:
            return jsonify({"error": "Submission not found."}), 404

        filename = os.path.basename(
            submission["medical_document"]
        )

        if not filename:
            return jsonify({"error": "Document not found."}), 404

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        if not os.path.isfile(file_path):
            return jsonify({"error": "Uploaded file is missing."}), 404

        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            filename,
            as_attachment=False
        )

    except (ValueError, TypeError):
        return jsonify({"error": "Invalid doctor ID."}), 400

    except Exception as error:
        print("Document Error:", error)
        return jsonify({"error": "Unable to open document."}), 500

    finally:
        if connection:
            cursor.close()
            connection.close()

@app.route("/medical-submissions/<int:submission_id>/status", methods=["PUT"])
def update_medical_submission_status(submission_id):
    data = request.get_json()

    user_id = data.get("user_id")
    status = data.get("status")
    doctor_remarks = data.get("doctor_remarks", "").strip()

    if not user_id or status not in ["accepted", "rejected"]:
        return jsonify({"message": "Invalid request"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT doctor_id FROM doctors WHERE user_id = %s",
            (user_id,)
        )
        doctor = cursor.fetchone()

        if not doctor:
            return jsonify({"message": "Doctor not found"}), 403

        cursor.execute("""
            SELECT status, patient_id
            FROM medical_submissions
            WHERE submission_id = %s
""", (submission_id,))

        submission = cursor.fetchone()

        if not submission:
            return jsonify({"message": "Submission not found"}), 404

        if submission["status"] != "pending":
            return jsonify({
                "message": "This submission has already been reviewed"
            }), 400

        cursor.execute("""
            UPDATE medical_submissions
            SET doctor_id = %s,
                status = %s,
                doctor_remarks = %s,
                reviewed_at = NOW()
            WHERE submission_id = %s
        """, (
            doctor["doctor_id"],
            status,
            doctor_remarks,
            submission_id
        ))

                # Get student user ID
        cursor.execute("""
            SELECT user_id
            FROM patients
            WHERE patient_id = %s
        """, (submission["patient_id"],))

        patient = cursor.fetchone()

        if not patient:
            connection.rollback()
            return jsonify({"message": "Patient not found"}), 404

        # Create notification
        title = "Medical Submission " + status.capitalize()

        message = (
            "Your medical submission has been "
            + status
            + " by the doctor."
        )

        cursor.execute("""
            INSERT INTO notifications
            (user_id, title, message, notification_type, is_read)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            patient["user_id"],
            title,
            message,
            "medical_submission",
            0
        ))

        connection.commit()

        return jsonify({
            "message": f"Medical submission {status} successfully"
        }), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@app.route("/student/medical-submissions/<int:user_id>", methods=["GET"])
def get_student_medical_submissions(user_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT patient_id
            FROM patients
            WHERE user_id = %s
        """, (user_id,))

        patient = cursor.fetchone()

        if not patient:
            return jsonify({"message": "Patient not found"}), 404

        cursor.execute("""
            SELECT
                submission_id,
                leave_from,
                leave_to,
                reason,
                medical_document,
                status,
                doctor_remarks,
                submitted_at,
                reviewed_at
            FROM medical_submissions
            WHERE patient_id = %s
            ORDER BY submitted_at DESC
        """, (patient["patient_id"],))

        submissions = cursor.fetchall()

        for item in submissions:
            for key in ["leave_from", "leave_to", "submitted_at", "reviewed_at"]:
                if item[key]:
                    item[key] = str(item[key])

        return jsonify({
            "submissions": submissions
        }), 200

    except Exception as error:
        print("Student Medical Submissions Error:", error)
        return jsonify({"message": "Unable to load submissions"}), 500

    finally:
        cursor.close()
        connection.close()

@app.route("/student/medical-submissions/<int:submission_id>/document", methods=["GET"])
def view_student_medical_certificate(submission_id):

    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"message": "User ID is required"}), 400

    connection = None
    cursor = None

    try:
        user_id = int(user_id)

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get student's patient ID
        cursor.execute("""
            SELECT patient_id
            FROM patients
            WHERE user_id = %s
        """, (user_id,))

        patient = cursor.fetchone()

        if not patient:
            return jsonify({"message": "Patient not found"}), 404

        # Check whether this submission belongs to the student
        cursor.execute("""
            SELECT medical_document
            FROM medical_submissions
            WHERE submission_id = %s
            AND patient_id = %s
        """, (submission_id, patient["patient_id"]))

        submission = cursor.fetchone()

        if not submission:
            return jsonify({"message": "Submission not found"}), 404

        filename = os.path.basename(
            submission["medical_document"]
        )

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        if not os.path.isfile(file_path):
            return jsonify({"message": "Document not found"}), 404

        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            filename,
            as_attachment=False
        )

    except (ValueError, TypeError):
        return jsonify({"message": "Invalid user ID"}), 400

    except Exception as error:
        print("Student Document Error:", error)
        return jsonify({"message": "Unable to open document"}), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

@app.route("/student/notifications/<int:user_id>", methods=["GET"])
def get_student_notifications(user_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT notification_id,
                   title,
                   message,
                   notification_type,
                   is_read,
                   created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))

        notifications = cursor.fetchall()

        return jsonify({
            "notifications": notifications
        }), 200

    except mysql.connector.Error as error:
        print("Notification Error:", error)
        return jsonify({
            "error": "Unable to load notifications."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close() 

@app.route("/student/notifications/<int:notification_id>/read", methods=["PUT"])
def mark_notification_as_read(notification_id):

    connection = None
    cursor = None

    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({
                "error": "User ID is required."
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check whether notification belongs to this user
        cursor.execute("""
            SELECT notification_id
            FROM notifications
            WHERE notification_id = %s
            AND user_id = %s
        """, (notification_id, user_id))

        notification = cursor.fetchone()

        if not notification:
            return jsonify({
                "error": "Notification not found."
            }), 404

        # Mark as read
        cursor.execute("""
            UPDATE notifications
            SET is_read = 1
            WHERE notification_id = %s
            AND user_id = %s
        """, (notification_id, user_id))

        connection.commit()

        return jsonify({
            "message": "Notification marked as read."
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
            
@app.route("/student/profile/<int:user_id>/picture", methods=["POST"])
def upload_student_profile_picture(user_id):

    connection = None
    cursor = None

    try:
        if "profile_picture" not in request.files:
            return jsonify({
                "error": "No profile picture selected."
            }), 400

        file = request.files["profile_picture"]

        if file.filename == "":
            return jsonify({
                "error": "Please select a picture."
            }), 400

        extension = file.filename.rsplit(".", 1)[-1].lower()

        if "." not in file.filename or extension not in ALLOWED_PROFILE_EXTENSIONS:
            return jsonify({
                "error": "Only JPG, JPEG and PNG images are allowed."
            }), 400

        unique_filename = str(uuid.uuid4()) + "." + extension

        saved_file_path = os.path.join(
            PROFILE_PICTURE_FOLDER,
            unique_filename
        )

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
                "error": "Student record not found."
            }), 404

        file.save(saved_file_path)

        relative_path = "profile_pictures/" + unique_filename

        cursor.execute("""
            UPDATE patients
            SET profile_picture = %s
            WHERE user_id = %s
        """, (relative_path, user_id))

        connection.commit()

        return jsonify({
            "message": "Profile picture uploaded successfully!",
            "profile_picture": relative_path
        }), 200

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()

        return jsonify({
            "error": str(error)
        }), 500

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close() 

@app.route("/student/profile-picture/<int:user_id>", methods=["GET"])
def get_student_profile_picture(user_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT profile_picture
            FROM patients
            WHERE user_id = %s
        """, (user_id,))

        patient = cursor.fetchone()

        if not patient or not patient["profile_picture"]:
            return jsonify({
                "error": "Profile picture not found."
            }), 404

        return send_from_directory(
            PROFILE_PICTURE_FOLDER,
            os.path.basename(patient["profile_picture"])
        )

    except mysql.connector.Error as error:
        return jsonify({
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()      

@app.route("/student/profile/<int:user_id>", methods=["PUT"])
def update_student_profile(user_id):

    data = request.get_json(silent=True) or {}

    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    contact_number = data.get("contact_number", "").strip()
    division = data.get("division", "").strip()

        # Validate email address
    import re

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({
            "error": "Please enter a valid email address."
        }), 400

    # Validate contact number
    if contact_number and (
        not contact_number.isdigit() or len(contact_number) != 10
    ):
        return jsonify({
            "error": "Contact number must contain exactly 10 digits."
        }), 400


    if not full_name or not email:
        return jsonify({
            "error": "Full name and email are required."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check whether the student account exists
        cursor.execute("""
            SELECT user_id
            FROM users
            WHERE user_id = %s
              AND role = 'student'
        """, (user_id,))

        student = cursor.fetchone()

        if not student:
            return jsonify({
                "error": "Student account not found."
            }), 404

        # Update user information
        cursor.execute("""
            UPDATE users
            SET full_name = %s,
                email = %s
            WHERE user_id = %s
        """, (full_name, email, user_id))

        # Update patient information
        cursor.execute("""
            UPDATE patients
            SET contact_number = %s,
                division = %s
            WHERE user_id = %s
        """, (
            contact_number or None,
            division or None,
            user_id
        ))

        connection.commit()

        return jsonify({
            "message": "Profile updated successfully!"
        }), 200

    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        return jsonify({
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    app.run(debug=True, port=5000)