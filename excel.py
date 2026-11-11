import openpyxl
from flask import Flask,render_template,flash,redirect,url_for

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'



path = "master.xlsx"

wb_obj = openpyxl.load_workbook(path)
ws = wb_obj.active
i=0

row_cells = ws[1]  


# Extract values from the row
row_values = [cell.value for cell in row_cells]
print(row_values)

for row in row_values:
    i=i+1
    print(row)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/trigger-alert')
def trigger_alert():
    flash('action complete')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)


    