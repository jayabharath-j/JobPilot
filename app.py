import csv
import io
import os

from datetime import date, datetime, timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "dev-secret-change-me"
)

app.config["MYSQL_HOST"] = os.getenv(
    "MYSQL_HOST",
    "localhost"
)

app.config["MYSQL_USER"] = os.getenv(
    "MYSQL_USER",
    "root"
)

app.config["MYSQL_PASSWORD"] = os.getenv(
    "MYSQL_PASSWORD",
    ""
)

app.config["MYSQL_DB"] = os.getenv(
    "MYSQL_DB",
    "jobtrack"
)

app.config["MYSQL_PORT"] = int(
    os.getenv("MYSQL_PORT", "3306")
)

app.config['MYSQL_SSL_MODE'] = 'REQUIRED'

mysql = MySQL(app)


# ============================================================
# CONSTANTS
# ============================================================

STATUSES = [
    "Applied",
    "Shortlisted",
    "Interview",
    "Selected",
    "Rejected",
    "Withdrawn",
]

JOB_TYPES = [
    "Full Time",
    "Part Time",
    "Internship",
    "Contract",
    "Remote",
]

INTERVIEW_MODES = [
    "Online",
    "Offline",
    "Phone",
]

FOLLOWUP_STATUSES = [
    "Pending",
    "Done",
    "Skipped",
]

PAGE_SIZE = 8


# ============================================================
# LOGIN REQUIRED DECORATOR
# ============================================================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if "user_id" not in session:
            flash(
                "Please log in first.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped


# ============================================================
# CSRF TOKEN
# ============================================================

def csrf_token():

    if "csrf_token" not in session:

        import secrets

        session["csrf_token"] = (
            secrets.token_urlsafe(32)
        )

    return session["csrf_token"]


# ============================================================
# BEFORE REQUEST
# CSRF PROTECTION + DATABASE MIGRATION
# ============================================================

@app.before_request
def protect_and_migrate():

    # --------------------------------------------------------
    # CSRF Protection
    # --------------------------------------------------------

    if request.method == "POST":

        expected = session.get(
            "csrf_token"
        )

        supplied = (
            request.form.get("csrf_token")
            or request.headers.get("X-CSRF-Token")
        )

        if expected and supplied != expected:

            return (
                "Invalid or missing CSRF token.",
                400
            )


    # --------------------------------------------------------
    # Database Migration
    # --------------------------------------------------------

    if not getattr(
        app,
        "_schema_ready",
        False
    ):

        try:

            cur = mysql.connection.cursor()


            # Application history table

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS application_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    application_id INT NOT NULL,
                    old_status VARCHAR(50),
                    new_status VARCHAR(50) NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    CONSTRAINT fk_history_app_final
                        FOREIGN KEY (application_id)
                        REFERENCES applications(id)
                        ON DELETE CASCADE,

                    INDEX idx_history_app_date_final
                        (application_id, changed_at)
                )
                """
            )


            # Check existing application columns

            cur.execute(
                "SHOW COLUMNS FROM applications"
            )

            cols = {
                row[0]
                for row in cur.fetchall()
            }


            # Required migrations

            migrations = {

                "is_favorite":
                    """
                    ALTER TABLE applications
                    ADD COLUMN is_favorite
                    TINYINT(1) NOT NULL DEFAULT 0
                    """,

                "follow_up_date":
                    """
                    ALTER TABLE applications
                    ADD COLUMN follow_up_date
                    DATE NULL
                    """,

                "follow_up_status":
                    """
                    ALTER TABLE applications
                    ADD COLUMN follow_up_status
                    VARCHAR(20) NOT NULL DEFAULT 'Pending'
                    """,

                "resume_version":
                    """
                    ALTER TABLE applications
                    ADD COLUMN resume_version
                    VARCHAR(120) NULL
                    """,

                "recruiter_name":
                    """
                    ALTER TABLE applications
                    ADD COLUMN recruiter_name
                    VARCHAR(120) NULL
                    """,

                "recruiter_email":
                    """
                    ALTER TABLE applications
                    ADD COLUMN recruiter_email
                    VARCHAR(180) NULL
                    """,

                "recruiter_phone":
                    """
                    ALTER TABLE applications
                    ADD COLUMN recruiter_phone
                    VARCHAR(40) NULL
                    """,
            }


            for col, sql in migrations.items():

                if col not in cols:

                    cur.execute(sql)


            mysql.connection.commit()

            cur.close()

            app._schema_ready = True


        except Exception:

            # Let the actual request surface
            # the database error.

            raise


# ============================================================
# GLOBAL TEMPLATE VARIABLES
# ============================================================

@app.context_processor
def inject_globals():

    return {

        "current_year":
            date.today().year,

        "statuses":
            STATUSES,

        "job_types":
            JOB_TYPES,

        "interview_modes":
            INTERVIEW_MODES,

        "followup_statuses":
            FOLLOWUP_STATUSES,

        "csrf_token":
            csrf_token(),

        "today":
            date.today(),
    }


# ============================================================
# CUSTOM JINJA FILTERS
# ============================================================

@app.template_filter("status_class")
def status_class(value):

    return (
        str(value or "")
        .lower()
        .replace(" ", "-")
    )


@app.template_filter("date_short")
def date_short(value):

    if not value:
        return "—"

    if hasattr(value, "strftime"):

        return value.strftime(
            "%d %b %Y"
        )

    try:

        return datetime.strptime(
            str(value),
            "%Y-%m-%d"
        ).strftime("%d %b %Y")

    except ValueError:

        return str(value)


@app.template_filter("time_short")
def time_short(value):

    if not value:
        return ""

    return str(value)[:5]


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "home.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm = request.form.get(
            "confirm_password",
            ""
        )


        if not name or not email or not password:

            flash(
                "All required fields must be filled.",
                "danger"
            )

            return render_template(
                "register.html"
            )


        if password != confirm:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return render_template(
                "register.html"
            )


        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )

            return render_template(
                "register.html"
            )


        cur = mysql.connection.cursor()

        cur.execute(
            """
            SELECT id
            FROM users
            WHERE email=%s
            """,
            (email,)
        )

        if cur.fetchone():

            cur.close()

            flash(
                "An account with this email already exists.",
                "danger"
            )

            return render_template(
                "register.html"
            )


        cur.execute(
            """
            INSERT INTO users
                (name, email, password_hash)
            VALUES
                (%s, %s, %s)
            """,
            (
                name,
                email,
                generate_password_hash(password),
            )
        )

        mysql.connection.commit()

        cur.close()


        flash(
            "Account created. You can now log in.",
            "success"
        )

        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        cur = mysql.connection.cursor()

        cur.execute(
            """
            SELECT id, name, email, password_hash
            FROM users
            WHERE email=%s
            """,
            (email,)
        )

        user = cur.fetchone()

        cur.close()


        if (
            not user
            or not check_password_hash(
                user[3],
                password
            )
        ):

            flash(
                "Invalid email or password.",
                "danger"
            )

            return render_template(
                "login.html"
            )


        session.clear()

        session["user_id"] = user[0]

        session["user_name"] = user[1]

        csrf_token()


        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "info"
    )

    return redirect(
        url_for("home")
    )


# ============================================================
# DASHBOARD DATA
# ============================================================

def fetch_dashboard_data(uid):

    cur = mysql.connection.cursor()


    # Total applications

    cur.execute(
        """
        SELECT COUNT(*)
        FROM applications
        WHERE user_id=%s
        """,
        (uid,)
    )

    total = cur.fetchone()[0]


    # Status counts

    counts = {}

    for status in STATUSES:

        cur.execute(
            """
            SELECT COUNT(*)
            FROM applications
            WHERE user_id=%s
            AND status=%s
            """,
            (uid, status)
        )

        counts[status] = cur.fetchone()[0]


    # Recent applications

    cur.execute(
        """
        SELECT
            a.*,
            COUNT(i.id) AS interview_count

        FROM applications a

        LEFT JOIN interviews i
            ON a.id = i.application_id

        WHERE a.user_id=%s

        GROUP BY a.id

        ORDER BY a.updated_at DESC

        LIMIT 8
        """,
        (uid,)
    )

    recent = cur.fetchall()


    # Upcoming interviews

    cur.execute(
        """
        SELECT
            i.*,
            a.company,
            a.role

        FROM interviews i

        JOIN applications a
            ON i.application_id = a.id

        WHERE a.user_id=%s
        AND i.interview_date >= CURDATE()

        ORDER BY
            i.interview_date,
            i.interview_time

        LIMIT 5
        """,
        (uid,)
    )

    upcoming = cur.fetchall()


    # Follow-ups due

    cur.execute(
        """
        SELECT COUNT(*)
        FROM applications

        WHERE user_id=%s
        AND follow_up_date IS NOT NULL
        AND follow_up_date <= CURDATE()
        AND follow_up_status='Pending'
        AND status NOT IN (
            'Rejected',
            'Withdrawn',
            'Selected'
        )
        """,
        (uid,)
    )

    followup_due = cur.fetchone()[0]


    # Favorites

    cur.execute(
        """
        SELECT COUNT(*)
        FROM applications

        WHERE user_id=%s
        AND is_favorite=1
        """,
        (uid,)
    )

    favorites = cur.fetchone()[0]


    # Interviews within 7 days

    cur.execute(
        """
        SELECT COUNT(*)

        FROM interviews i

        JOIN applications a
            ON i.application_id = a.id

        WHERE a.user_id=%s

        AND i.interview_date
            BETWEEN CURDATE()
            AND DATE_ADD(
                CURDATE(),
                INTERVAL 7 DAY
            )
        """,
        (uid,)
    )

    interviews_7d = cur.fetchone()[0]


    cur.close()


    # Rates

    interview_rate = (
        round(
            (
                counts["Interview"]
                + counts["Selected"]
            )
            / total
            * 100,
            1
        )
        if total
        else 0
    )


    selection_rate = (
        round(
            counts["Selected"]
            / total
            * 100,
            1
        )
        if total
        else 0
    )


    return locals()


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    data = fetch_dashboard_data(
        session["user_id"]
    )

    return render_template(
        "dashboard.html",
        **data
    )


# ============================================================
# APPLICATIONS
# ============================================================

@app.route("/applications")
@login_required
def applications():

    uid = session["user_id"]

    q = request.args.get(
        "q",
        ""
    ).strip()

    status = request.args.get(
        "status",
        ""
    ).strip()

    job_type = request.args.get(
        "job_type",
        ""
    ).strip()

    location = request.args.get(
        "location",
        ""
    ).strip()

    favorite = request.args.get(
        "favorite",
        ""
    ).strip()

    followup = request.args.get(
        "followup",
        ""
    ).strip()

    page = max(
        1,
        request.args.get(
            "page",
            1,
            type=int
        )
    )


    sql = """
        SELECT
            a.*,
            COUNT(i.id) AS interview_count

        FROM applications a

        LEFT JOIN interviews i
            ON a.id = i.application_id

        WHERE a.user_id=%s
    """

    params = [uid]


    # Search

    if q:

        sql += """
            AND (
                a.company LIKE %s
                OR a.role LIKE %s
                OR a.location LIKE %s
                OR a.recruiter_name LIKE %s
            )
        """

        like = f"%{q}%"

        params += [like] * 4


    # Status

    if status in STATUSES:

        sql += """
            AND a.status=%s
        """

        params.append(status)


    # Job type

    if job_type in JOB_TYPES:

        sql += """
            AND a.job_type=%s
        """

        params.append(job_type)


    # Location

    if location:

        sql += """
            AND a.location LIKE %s
        """

        params.append(
            f"%{location}%"
        )


    # Favorites

    if favorite == "1":

        sql += """
            AND a.is_favorite=1
        """


    # Follow-ups

    if followup == "due":

        sql += """
            AND a.follow_up_date IS NOT NULL
            AND a.follow_up_date <= CURDATE()
            AND a.follow_up_status='Pending'
        """


    sql += """
        GROUP BY a.id

        ORDER BY
            a.is_favorite DESC,
            a.application_date DESC,
            a.id DESC
    """


    cur = mysql.connection.cursor()

    cur.execute(
        sql,
        tuple(params)
    )

    rows = cur.fetchall()

    cur.close()


    total = len(rows)

    start = (
        page - 1
    ) * PAGE_SIZE

    paged = rows[
        start:start + PAGE_SIZE
    ]

    pages = max(
        1,
        (
            total + PAGE_SIZE - 1
        ) // PAGE_SIZE
    )


    return render_template(
        "applications.html",
        applications=paged,
        total=total,
        page=page,
        pages=pages,
        q=q,
        selected_status=status,
        selected_job_type=job_type,
        location=location,
        favorite=favorite,
        followup=followup,
    )


# ============================================================
# ADD APPLICATION
# ============================================================

@app.route(
    "/applications/add",
    methods=["GET", "POST"]
)
@login_required
def add_application():

    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        role = request.form.get(
            "role",
            ""
        ).strip()

        application_date = request.form.get(
            "application_date",
            ""
        )

        status = request.form.get(
            "status",
            "Applied"
        )

        job_type = request.form.get(
            "job_type",
            "Full Time"
        )


        if (
            not company
            or not role
            or not application_date
        ):

            flash(
                "Company, role and application date are required.",
                "danger"
            )

            return render_template(
                "application_form.html",
                mode="Add",
                today=date.today().isoformat()
            )


        if status not in STATUSES:
            status = "Applied"

        if job_type not in JOB_TYPES:
            job_type = "Full Time"


        cur = mysql.connection.cursor()


        cur.execute(
            """
            INSERT INTO applications (
                user_id,
                company,
                role,
                location,
                job_type,
                salary,
                application_date,
                job_url,
                status,
                notes,
                is_favorite,
                follow_up_date,
                follow_up_status,
                resume_version,
                recruiter_name,
                recruiter_email,
                recruiter_phone
            )

            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            """,
            (
                session["user_id"],
                company,
                role,
                request.form.get(
                    "location",
                    ""
                ).strip(),

                job_type,

                request.form.get(
                    "salary",
                    ""
                ).strip(),

                application_date,

                request.form.get(
                    "job_url",
                    ""
                ).strip(),

                status,

                request.form.get(
                    "notes",
                    ""
                ).strip(),

                1
                if request.form.get(
                    "is_favorite"
                )
                else 0,

                request.form.get(
                    "follow_up_date"
                )
                or None,

                request.form.get(
                    "follow_up_status",
                    "Pending"
                ),

                request.form.get(
                    "resume_version",
                    ""
                ).strip(),

                request.form.get(
                    "recruiter_name",
                    ""
                ).strip(),

                request.form.get(
                    "recruiter_email",
                    ""
                ).strip(),

                request.form.get(
                    "recruiter_phone",
                    ""
                ).strip(),
            )
        )


        app_id = cur.lastrowid


        cur.execute(
            """
            INSERT INTO application_history (
                application_id,
                old_status,
                new_status
            )

            VALUES (
                %s,
                NULL,
                %s
            )
            """,
            (
                app_id,
                status
            )
        )


        mysql.connection.commit()

        cur.close()


        flash(
            "Application added successfully.",
            "success"
        )

        return redirect(
            url_for(
                "application_detail",
                app_id=app_id
            )
        )


    return render_template(
        "application_form.html",
        mode="Add",
        today=date.today().isoformat()
    )


# ============================================================
# EDIT APPLICATION
# ============================================================

@app.route(
    "/applications/<int:app_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_application(app_id):

    uid = session["user_id"]

    cur = mysql.connection.cursor()


    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        role = request.form.get(
            "role",
            ""
        ).strip()

        application_date = request.form.get(
            "application_date",
            ""
        )

        status = request.form.get(
            "status",
            "Applied"
        )

        job_type = request.form.get(
            "job_type",
            "Full Time"
        )


        cur.execute(
            """
            SELECT status
            FROM applications
            WHERE id=%s
            AND user_id=%s
            """,
            (app_id, uid)
        )

        old = cur.fetchone()


        if not old:

            cur.close()

            flash(
                "Application not found.",
                "danger"
            )

            return redirect(
                url_for("applications")
            )


        if (
            not company
            or not role
            or not application_date
        ):

            cur.close()

            flash(
                "Company, role and application date are required.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_application",
                    app_id=app_id
                )
            )


        if status not in STATUSES:
            status = "Applied"

        if job_type not in JOB_TYPES:
            job_type = "Full Time"


        cur.execute(
            """
            UPDATE applications

            SET
                company=%s,
                role=%s,
                location=%s,
                job_type=%s,
                salary=%s,
                application_date=%s,
                job_url=%s,
                status=%s,
                notes=%s,
                is_favorite=%s,
                follow_up_date=%s,
                follow_up_status=%s,
                resume_version=%s,
                recruiter_name=%s,
                recruiter_email=%s,
                recruiter_phone=%s

            WHERE id=%s
            AND user_id=%s
            """,
            (
                company,
                role,

                request.form.get(
                    "location",
                    ""
                ).strip(),

                job_type,

                request.form.get(
                    "salary",
                    ""
                ).strip(),

                application_date,

                request.form.get(
                    "job_url",
                    ""
                ).strip(),

                status,

                request.form.get(
                    "notes",
                    ""
                ).strip(),

                1
                if request.form.get(
                    "is_favorite"
                )
                else 0,

                request.form.get(
                    "follow_up_date"
                )
                or None,

                request.form.get(
                    "follow_up_status",
                    "Pending"
                ),

                request.form.get(
                    "resume_version",
                    ""
                ).strip(),

                request.form.get(
                    "recruiter_name",
                    ""
                ).strip(),

                request.form.get(
                    "recruiter_email",
                    ""
                ).strip(),

                request.form.get(
                    "recruiter_phone",
                    ""
                ).strip(),

                app_id,
                uid,
            )
        )


        # Save status history

        if old[0] != status:

            cur.execute(
                """
                INSERT INTO application_history (
                    application_id,
                    old_status,
                    new_status
                )

                VALUES (
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    app_id,
                    old[0],
                    status
                )
            )


        mysql.connection.commit()

        cur.close()


        flash(
            "Application updated.",
            "success"
        )

        return redirect(
            url_for(
                "application_detail",
                app_id=app_id
            )
        )


    cur.execute(
        """
        SELECT *
        FROM applications

        WHERE id=%s
        AND user_id=%s
        """,
        (app_id, uid)
    )

    application = cur.fetchone()

    cur.close()


    if not application:

        flash(
            "Application not found.",
            "danger"
        )

        return redirect(
            url_for("applications")
        )


    return render_template(
        "application_form.html",
        mode="Edit",
        application=application
    )


# ============================================================
# APPLICATION DETAIL
# ============================================================

@app.route(
    "/applications/<int:app_id>"
)
@login_required
def application_detail(app_id):

    uid = session["user_id"]

    cur = mysql.connection.cursor()


    cur.execute(
        """
        SELECT *
        FROM applications

        WHERE id=%s
        AND user_id=%s
        """,
        (app_id, uid)
    )

    application = cur.fetchone()


    if not application:

        cur.close()

        flash(
            "Application not found.",
            "danger"
        )

        return redirect(
            url_for("applications")
        )


    # Status history

    cur.execute(
        """
        SELECT
            old_status,
            new_status,
            changed_at

        FROM application_history

        WHERE application_id=%s

        ORDER BY
            changed_at DESC,
            id DESC
        """,
        (app_id,)
    )

    history = cur.fetchall()


    # Interviews

    cur.execute(
        """
        SELECT *
        FROM interviews

        WHERE application_id=%s

        ORDER BY
            interview_date DESC,
            interview_time DESC
        """,
        (app_id,)
    )

    interview_rows = cur.fetchall()

    cur.close()


    return render_template(
        "application_detail.html",
        application=application,
        history=history,
        interview_rows=interview_rows
    )


# ============================================================
# DELETE APPLICATION
# ============================================================

@app.post(
    "/applications/<int:app_id>/delete"
)
@login_required
def delete_application(app_id):

    cur = mysql.connection.cursor()

    cur.execute(
        """
        DELETE FROM applications

        WHERE id=%s
        AND user_id=%s
        """,
        (
            app_id,
            session["user_id"]
        )
    )

    mysql.connection.commit()

    deleted = cur.rowcount

    cur.close()


    flash(
        "Application deleted."
        if deleted
        else "Application not found.",

        "success"
        if deleted
        else "danger"
    )


    return redirect(
        url_for("applications")
    )


# ============================================================
# TOGGLE FAVORITE
# ============================================================

@app.post(
    "/applications/<int:app_id>/favorite"
)
@login_required
def toggle_favorite(app_id):

    cur = mysql.connection.cursor()

    cur.execute(
        """
        UPDATE applications

        SET is_favorite = 1 - is_favorite

        WHERE id=%s
        AND user_id=%s
        """,
        (
            app_id,
            session["user_id"]
        )
    )

    mysql.connection.commit()

    cur.close()


    return redirect(
        request.referrer
        or url_for("applications")
    )


# ============================================================
# INTERVIEWS
# ============================================================

@app.route(
    "/interviews",
    methods=["GET", "POST"]
)
@login_required
def interviews():

    uid = session["user_id"]

    cur = mysql.connection.cursor()


    if request.method == "POST":

        # Verify application ownership

        cur.execute(
            """
            SELECT a.id
            FROM applications a

            WHERE a.id=%s
            AND a.user_id=%s
            """,
            (
                request.form.get(
                    "application_id"
                ),
                uid
            )
        )


        if not cur.fetchone():

            cur.close()

            flash(
                "Invalid application.",
                "danger"
            )

            return redirect(
                url_for("interviews")
            )


        interview_date = request.form.get(
            "interview_date"
        )


        if not interview_date:

            cur.close()

            flash(
                "Interview date is required.",
                "danger"
            )

            return redirect(
                url_for("interviews")
            )


        mode = request.form.get(
            "mode",
            "Online"
        )

        if mode not in INTERVIEW_MODES:
            mode = "Online"


        cur.execute(
            """
            INSERT INTO interviews (
                application_id,
                interview_date,
                interview_time,
                round_name,
                mode,
                notes
            )

            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                request.form.get(
                    "application_id"
                ),

                interview_date,

                request.form.get(
                    "interview_time"
                )
                or None,

                request.form.get(
                    "round_name",
                    ""
                ).strip(),

                mode,

                request.form.get(
                    "notes",
                    ""
                ).strip(),
            )
        )


        mysql.connection.commit()

        cur.close()


        flash(
            "Interview added.",
            "success"
        )

        return redirect(
            url_for("interviews")
        )


    # Applications for dropdown

    cur.execute(
        """
        SELECT
            a.id,
            a.company,
            a.role

        FROM applications a

        WHERE a.user_id=%s

        ORDER BY a.company
        """,
        (uid,)
    )

    apps = cur.fetchall()


    # Interview list

    cur.execute(
        """
        SELECT
            i.*,
            a.company,
            a.role

        FROM interviews i

        JOIN applications a
            ON i.application_id = a.id

        WHERE a.user_id=%s

        ORDER BY
            i.interview_date ASC,
            i.interview_time ASC
        """,
        (uid,)
    )

    rows = cur.fetchall()

    cur.close()


    return render_template(
        "interviews.html",
        interviews=rows,
        applications=apps,
        today=date.today()
    )


# ============================================================
# EDIT INTERVIEW
# ============================================================

@app.route(
    "/interviews/<int:interview_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_interview(interview_id):

    uid = session["user_id"]

    cur = mysql.connection.cursor()


    if request.method == "POST":

        mode = request.form.get(
            "mode",
            "Online"
        )

        if mode not in INTERVIEW_MODES:
            mode = "Online"


        if not request.form.get(
            "interview_date"
        ):

            cur.close()

            flash(
                "Interview date is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_interview",
                    interview_id=interview_id
                )
            )


        cur.execute(
            """
            UPDATE interviews i

            JOIN applications a
                ON i.application_id = a.id

            SET
                i.interview_date=%s,
                i.interview_time=%s,
                i.round_name=%s,
                i.mode=%s,
                i.notes=%s

            WHERE i.id=%s
            AND a.user_id=%s
            """,
            (
                request.form.get(
                    "interview_date"
                ),

                request.form.get(
                    "interview_time"
                )
                or None,

                request.form.get(
                    "round_name",
                    ""
                ).strip(),

                mode,

                request.form.get(
                    "notes",
                    ""
                ).strip(),

                interview_id,
                uid,
            )
        )


        mysql.connection.commit()

        cur.close()


        flash(
            "Interview updated.",
            "success"
        )

        return redirect(
            url_for("interviews")
        )


    cur.execute(
        """
        SELECT i.*

        FROM interviews i

        JOIN applications a
            ON i.application_id = a.id

        WHERE i.id=%s
        AND a.user_id=%s
        """,
        (
            interview_id,
            uid
        )
    )

    interview = cur.fetchone()

    cur.close()


    if not interview:

        flash(
            "Interview not found.",
            "danger"
        )

        return redirect(
            url_for("interviews")
        )


    return render_template(
        "interview_edit.html",
        interview=interview
    )


# ============================================================
# DELETE INTERVIEW
# ============================================================

@app.post(
    "/interviews/<int:interview_id>/delete"
)
@login_required
def delete_interview(interview_id):

    cur = mysql.connection.cursor()

    cur.execute(
        """
        DELETE i

        FROM interviews i

        JOIN applications a
            ON i.application_id = a.id

        WHERE i.id=%s
        AND a.user_id=%s
        """,
        (
            interview_id,
            session["user_id"]
        )
    )

    mysql.connection.commit()

    deleted = cur.rowcount

    cur.close()


    flash(
        "Interview deleted."
        if deleted
        else "Interview not found.",

        "success"
        if deleted
        else "danger"
    )


    return redirect(
        url_for("interviews")
    )


# ============================================================
# ANALYTICS
# ============================================================

@app.route("/analytics")
@login_required
def analytics():

    uid = session["user_id"]

    cur = mysql.connection.cursor()


    # Status breakdown

    cur.execute(
        """
        SELECT
            status,
            COUNT(*)

        FROM applications

        WHERE user_id=%s

        GROUP BY status
        """,
        (uid,)
    )

    status_rows = cur.fetchall()


    # Monthly applications

    cur.execute(
        """
        SELECT
            DATE_FORMAT(
                application_date,
                '%%Y-%%m'
            ) AS month,
            COUNT(*)

        FROM applications

        WHERE user_id=%s

        GROUP BY month

        ORDER BY month
        """,
        (uid,)
    )

    monthly_rows = cur.fetchall()


    # Job types

    cur.execute(
        """
        SELECT
            job_type,
            COUNT(*)

        FROM applications

        WHERE user_id=%s

        GROUP BY job_type

        ORDER BY COUNT(*) DESC
        """,
        (uid,)
    )

    type_rows = cur.fetchall()


    # Locations

    cur.execute(
        """
        SELECT
            location,
            COUNT(*)

        FROM applications

        WHERE user_id=%s

        AND location IS NOT NULL
        AND location<>''

        GROUP BY location

        ORDER BY COUNT(*) DESC

        LIMIT 8
        """,
        (uid,)
    )

    location_rows = cur.fetchall()


    # Companies

    cur.execute(
        """
        SELECT
            company,
            COUNT(*)

        FROM applications

        WHERE user_id=%s

        GROUP BY company

        ORDER BY
            COUNT(*) DESC,
            company

        LIMIT 10
        """,
        (uid,)
    )

    company_rows = cur.fetchall()


    # Summary

    cur.execute(
        """
        SELECT
            COUNT(*),
            SUM(status='Selected'),
            SUM(status='Rejected'),
            SUM(status='Interview')

        FROM applications

        WHERE user_id=%s
        """,
        (uid,)
    )

    summary = cur.fetchone()

    cur.close()


    return render_template(
        "analytics.html",
        status_rows=status_rows,
        monthly_rows=monthly_rows,
        type_rows=type_rows,
        location_rows=location_rows,
        company_rows=company_rows,
        summary=summary
    )


# ============================================================
# CSV EXPORT
# ============================================================

@app.route(
    "/export/applications.csv"
)
@login_required
def export_applications():

    uid = session["user_id"]

    cur = mysql.connection.cursor()


    cur.execute(
        """
        SELECT
            company,
            role,
            location,
            job_type,
            salary,
            application_date,
            status,
            job_url,
            notes,
            is_favorite,
            follow_up_date,
            follow_up_status,
            resume_version,
            recruiter_name,
            recruiter_email,
            recruiter_phone

        FROM applications

        WHERE user_id=%s

        ORDER BY application_date DESC
        """,
        (uid,)
    )

    rows = cur.fetchall()

    cur.close()


    output = io.StringIO()

    writer = csv.writer(output)


    writer.writerow([
        "Company",
        "Role",
        "Location",
        "Job Type",
        "Salary",
        "Application Date",
        "Status",
        "Job URL",
        "Notes",
        "Favorite",
        "Follow-up Date",
        "Follow-up Status",
        "Resume Version",
        "Recruiter Name",
        "Recruiter Email",
        "Recruiter Phone",
    ])


    writer.writerows(rows)


    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=jobpilot_applications.csv"
        }
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "app": "JobPilot",
        "version": "Final"
    }


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
