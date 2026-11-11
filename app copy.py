from flask import Flask, render_template, request, redirect, url_for
from extensions import db
from models import Customer, Device, WorkOrder

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

@app.route('/excel-upload', methods=["GET", "POST"])
def excel_check():
    print

if __name__ == "__main__":
    app.run(debug=True)