from flask import Flask, render_template, request, redirect, url_for
from extensions import db
from models import Customer, Device, WorkOrder
from werkzeug.utils import secure_filename
import os
import openpyxl
import datetime
import re

app = Flask(__name__)
app.secret_key = "secret_key_for_flash_messages"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///service_reports.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route("/")
def index():
    orders = WorkOrder.query.all()
    return render_template("index.html", orders=orders)

@app.route("/add", methods=["GET", "POST"])
def add_report():
    if request.method == "POST":
        try:
            wo_no = request.form.get("work_order_no")
            if WorkOrder.query.filter_by(work_order_no=wo_no).first():
                return f"Error: Work Order '{wo_no}' already exists! <a href='/add'>Go Back</a>"

            # 1. Handle Customer (Match by address and name)
            addr = request.form.get("customer_address")
            name = request.form.get("customer_name")
            phone = request.form.get("contact_number")
            
            customer = Customer.query.filter_by(customer_address=addr, customer_name=name).first()
            if not customer:
                customer = Customer(customer_address=addr, customer_name=name, contact_number=phone)
                db.session.add(customer)
                db.session.commit()

            # 2. Handle Device (Only match if serial number is provided and not empty)
            u_desc = request.form.get("unit_description")
            brand = request.form.get("brand")
            model = request.form.get("model")
            serial = request.form.get("serial_number").strip()

            device = None
            if serial:
                device = Device.query.filter_by(serial_number=serial).first()
            
            if not device:
                device = Device(
                    customer_id=customer.id,
                    unit_description=u_desc,
                    brand=brand,
                    model=model,
                    serial_number=serial if serial else None
                )
                db.session.add(device)
                db.session.commit()

            # 3. Create Work Order
            new_wo = WorkOrder(
                work_order_no=wo_no,
                date=request.form.get("date"),
                customer_id=customer.id,
                device_id=device.id,
                breakdown=request.form.get("breakdown"),
                work_carried_out=request.form.get("work_carried_out"),
                spare_item=request.form.get("spare_item")
            )
            db.session.add(new_wo)
            db.session.commit()
            return redirect(url_for("index"))
            
        except Exception as e:
            db.session.rollback()
            return f"Database Error occurred: {str(e)} <br><a href='/add'>Go Back</a>"

    suggestions = {
        "addresses": [r[0] for r in db.session.query(Customer.customer_address.distinct()).all() if r[0]],
        "names": [r[0] for r in db.session.query(Customer.customer_name.distinct()).all() if r[0]],
        "units": [r[0] for r in db.session.query(Device.unit_description.distinct()).all() if r[0]],
        "brands": [r[0] for r in db.session.query(Device.brand.distinct()).all() if r[0]],
        "models": [r[0] for r in db.session.query(Device.model.distinct()).all() if r[0]],
    }

    return render_template("report_form.html", order=None, sug=suggestions)

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_report(id):
    wo = WorkOrder.query.get_or_404(id)

    if request.method == "POST":
        if "delete_btn" in request.form:
            try:
                db.session.delete(wo)
                db.session.commit()
                return redirect(url_for("index"))
            except Exception as e:
                db.session.rollback()
                return f"Error deleting record: {str(e)} <br><a href='/edit/{id}'>Go Back</a>"

        try:
            # We don't modify work_order_no since it's locked/readonly on the form
            wo.date = request.form.get("date")
            
            wo.customer.customer_address = request.form.get("customer_address")
            wo.customer.customer_name = request.form.get("customer_name")
            wo.customer.contact_number = request.form.get("contact_number")
            
            wo.device.unit_description = request.form.get("unit_description")
            wo.device.brand = request.form.get("brand")
            wo.device.model = request.form.get("model")
            wo.device.serial_number = request.form.get("serial_number")
            
            wo.breakdown = request.form.get("breakdown")
            wo.work_carried_out = request.form.get("work_carried_out")
            wo.spare_item = request.form.get("spare_item")

            db.session.commit()
            return redirect(url_for("index"))
            
        except Exception as e:
            db.session.rollback()
            return f"Database Error during update: {str(e)} <br><a href='/edit/{id}'>Go Back</a>"

    suggestions = {
        "addresses": [r[0] for r in db.session.query(Customer.customer_address.distinct()).all() if r[0]],
        "names": [r[0] for r in db.session.query(Customer.customer_name.distinct()).all() if r[0]],
        "units": [r[0] for r in db.session.query(Device.unit_description.distinct()).all() if r[0]],
        "brands": [r[0] for r in db.session.query(Device.brand.distinct()).all() if r[0]],
        "models": [r[0] for r in db.session.query(Device.model.distinct()).all() if r[0]],
    }

    return render_template("report_form.html", order=wo, sug=suggestions)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER , exist_ok=True)


@app.route('/upload', methods=["POST"])
def excel_check():
    if 'excel-upload' not in request.files:
        return "No file uploaded. <a href='/'>Go Back</a>"
        
    file = request.files['excel-upload']
    if file.filename == '':
        return "No selected file. <a href='/'>Go Back</a>"

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            wb = openpyxl.load_workbook(filepath, data_only=True)
            ws = wb.active
            
            imported_list = []
            duplicate_list = []
            conflict_list = []

            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or not row[0]:
                    continue

                wo_no = str(row[0]).strip()

                # Parse date from Excel
                raw_date = row[1]
                if isinstance(raw_date, (datetime.datetime, datetime.date)):
                    date_str = raw_date.strftime("%Y-%m-%d")
                else:
                    date_str = str(raw_date).split()[0] if raw_date else ""

                unit_desc = str(row[5]).strip() if row[5] and str(row[5]).strip() != "None" else ""
                serial = str(row[8]).strip() if row[8] and str(row[8]).strip() not in ["-", "None"] else ""

                # Check if Work Order already exists in DB
                existing_wo = WorkOrder.query.filter_by(work_order_no=wo_no).first()

                if existing_wo:
                    # Compare details to see if it's an exact duplicate or a conflict
                    matches_date = (existing_wo.date == date_str)
                    matches_unit = (existing_wo.device.unit_description == unit_desc)
                    matches_serial = (str(existing_wo.device.serial_number or '') == str(serial))

                    if matches_date and matches_unit and matches_serial:
                        # True exact duplicate
                        duplicate_list.append(wo_no)
                    else:
                        # Conflict: Same ID, but different details!
                        conflict_detail = {
                            "wo": wo_no,
                            "excel_info": f"Date: {date_str} | Unit: {unit_desc} | S/N: {serial}",
                            "db_info": f"Date: {existing_wo.date} | Unit: {existing_wo.device.unit_description} | S/N: {existing_wo.device.serial_number}"
                        }
                        conflict_list.append(conflict_detail)
                    continue

                # --- Rest of normal import logic for new rows ---
                raw_contact_cell = str(row[2]).strip() if row[2] and str(row[2]).strip() != "None" else ""
                phone_matches = re.findall(r'(?:0\d{1,2}[-\s]?\d{7}|0\d{2}[-\s]?\d{3}[-\s]?\d{4})', raw_contact_cell)
                phone_number = ", ".join(phone_matches) if phone_matches else "-"
                customer_name = raw_contact_cell

                address = str(row[3]).strip() if row[3] and str(row[3]).strip() != "None" else "Unknown Address"
                if len(row) > 4 and row[4] and str(row[4]).strip() != "None":
                    address = f"{address} ({str(row[4]).strip()})"

                customer = Customer.query.filter_by(customer_address=address, customer_name=customer_name).first()
                if not customer:
                    customer = Customer(
                        customer_address=address, 
                        customer_name=customer_name, 
                        contact_number=phone_number
                    )
                    db.session.add(customer)
                    db.session.commit()

                brand = str(row[6]).strip() if row[6] and str(row[6]).strip() != "None" else ""
                model = str(row[7]).strip() if row[7] and str(row[7]).strip() != "None" else ""
                serial_val = serial if serial else None

                device = None
                if serial_val:
                    device = Device.query.filter_by(serial_number=serial_val).first()

                if not device:
                    device = Device(
                        customer_id=customer.id,
                        unit_description=unit_desc,
                        brand=brand,
                        model=model,
                        serial_number=serial_val
                    )
                    db.session.add(device)
                    db.session.commit()

                breakdown = str(row[10]).strip() if len(row) > 10 and row[10] and str(row[10]).strip() != "None" else ""
                work_carried = str(row[11]).strip() if len(row) > 11 and row[11] and str(row[11]).strip() != "None" else ""
                spare_item = str(row[13]).strip() if len(row) > 13 and row[13] and str(row[13]).strip() != "None" else ""

                new_wo = WorkOrder(
                    work_order_no=wo_no,
                    date=date_str,
                    customer_id=customer.id,
                    device_id=device.id,
                    breakdown=breakdown,
                    work_carried_out=work_carried,
                    spare_item=spare_item
                )
                db.session.add(new_wo)
                imported_list.append(wo_no)

            db.session.commit()
            
            if os.path.exists(filepath):
                os.remove(filepath)
                
            return render_template("upload_summary.html", imported=imported_list, duplicates=duplicate_list, conflicts=conflict_list)

        except Exception as e:
            db.session.rollback()
            return f"Error processing Excel file: {str(e)} <br><a href='/'>Go Back</a>"

    return redirect(url_for('index'))
    

if __name__ == "__main__":
    app.run(debug=True)