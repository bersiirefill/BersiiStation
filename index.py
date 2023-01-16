'''
Bersii Refill Station - V1.0
Code created by Matt Richardson 
Modified by Hanustavira Guru Acarya
for details, visit:  http://mattrichardson.com/Raspberry-Pi-Flask/inde...
'''
import requests
import json
import RPi.GPIO as GPIO
from flask import Flask, request, render_template, session, url_for, redirect

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
# Atur pin GPIO mesin refill
refill = 12
# Atur status mesin refill
refillSts = 0
# Atur pin GPIO mesin refill sebagai output
GPIO.setup(refill, GPIO.OUT) 
# Matikan mesin refill saat rpi menyala 
GPIO.output(refill, GPIO.LOW)

# Serial Number - Nomor Seri
def getserial():
  # Ambil nomor seri
  cpuserial = "0000000000000000"
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if line[0:6]=='Serial':
        cpuserial = line[10:26]
    f.close()
  except:
    cpuserial = "ERROR000000000"
  return cpuserial

def revoke_token(sessions, status):
   ssn_id = sessions.split('|')[0]
   # Data yang dikirim ke API
   serial = {'nomor_seri':getserial(), 'token_id':ssn_id}
   # Kirim POST ke server dan simpan sebagai object
   tokenizes_r = requests.post(url = "http://192.168.1.70:8000/api/revoke_station", data = serial, headers = {"Accept": "application/json", "Authorization": "Bearer " + sessions})
   loads = tokenizes_r.json()
   message = loads["message"]
   if message == "Token Dicabut":
      if status == "user":
         session.pop("token", None)
      else:
         session.pop("id_admin", None)
         session.pop("nama_admin", None)
         session.pop("email_admin", None)
         session.pop("jabatan_admin", None)
         session.pop("token_admin", None)
   else:
      print("Token Gagal Dicabut")
   return message
   
def revoke_all():
   # Data yang dikirim ke API
   serial = {'nomor_seri':getserial()}
   # Kirim POST ke server dan simpan sebagai object
   tokenizes_r = requests.post(url = "http://192.168.1.70:8000/api/revoke_all", data = serial, headers = {"Accept": "application/json"})
   loads = tokenizes_r.json()
   message = loads["message"]
   if message == "Token Dicabut":
      session.pop("token", None)
      session.pop("token_admin", None)
   else:
      print("Token Gagal Dicabut")
   return message

@app.route("/<action>")
def action(action):
   if action == "on":
      GPIO.output(refill, GPIO.HIGH)
   if action == "off":
      GPIO.output(refill, GPIO.LOW)
   refillSts = GPIO.input(refill)
   templateData = {
      'status' : refillSts,
   }
   return render_template('index.html', **templateData)

# Bagian Admin
@app.route("/hardware_admin")
def hardware_admin():
   f = open('/proc/cpuinfo','r')
   templateData = {
      'hardware' : f,
   }
   return render_template('hardware_admin.html', **templateData)

@app.route("/index_admin")
def index_admin():
   admin_ssn = session["token_admin"]
   # Data yang dikirim ke API
   data = {'nomor_seri':getserial()}
   # Kirim POST ke server dan simpan sebagai object
   rqs = requests.post(url = "http://192.168.1.70:8000/api/station_stock", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
   rds = rqs.json()
   nama_produk = rds["data"][0]["nama_produk"]
   stok_produk = rds["data"][0]["stok"]
   templateData = {
      'nama_produk' : nama_produk,
      'stok_produk' : stok_produk,
   }
   return render_template('index_admin.html', **templateData)
   
@app.route("/hwstatus_admin", methods =["GET", "POST"])
def hwstatus_admin():
   admin_ssn = session["token_admin"]
   if request.method == "POST":
      stat = request.form.get("stat")
      # Data yang dikirim ke API
      data = {'nomor_seri':getserial(), 'status':stat}
      # Kirim POST ke server dan simpan sebagai object
      rqs = requests.post(url = "http://192.168.1.70:8000/api/change_station_status", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
      rds = rqs.json()
      msg = rds["message"]
      return redirect(url_for("hwstatus_admin"))
      
   # Data yang dikirim ke API
   data = {'nomor_seri':getserial()}
   # Kirim POST ke server dan simpan sebagai object
   r = requests.post(url = "http://192.168.1.70:8000/api/station_status", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
   loads = r.json()
   templateData = {
      'nomor_seri' : getserial(),
      'latitude' : loads["data"]["latitude"],
      'longitude' : loads["data"]["longitude"],
      'status_mesin' : loads["data"]["status_mesin"],
      'alamat' : loads["data"]["alamat"],
      'update_terakhir' : loads["data"]["update_terakhir"],
   }
   return render_template('hwstatus_admin.html', **templateData)

@app.route("/login_admin", methods =["GET", "POST"])
def login_admin():
   if request.method == "POST":
       # Baca input form HTML
       email = request.form.get("email")
       password = request.form.get("password")
       # Data yang dikirim ke API
       data = {'email':email, 'password':password, 'nomor_seri':getserial()}
       # Kirim POST ke server dan simpan sebagai object
       r = requests.post(url = "http://192.168.1.70:8000/api/login_station_admin", data = data, headers = {"Accept": "application/json"})
       loads = r.json()
       # Fetch
       id_admin = loads["data"]["id_admin"]
       nama_admin = loads["data"]["nama"]
       email_admin = loads["data"]["email"]
       jabatan_admin = loads["data"]["jabatan"]
       token_admin = loads["data"]["token"]
       # Masukkan ke session
       session["id_admin"] = id_admin
       session["nama_admin"] = nama_admin
       session["email_admin"] = email_admin
       session["jabatan_admin"] = jabatan_admin
       session["token_admin"] = token_admin
       return redirect(url_for("index_admin"))
   return render_template("login_admin.html")
   
@app.route("/logout_admin", methods =["GET", "POST"])
def logout_admin():
   admin_ssn = session["token_admin"]
   revoke = revoke_token(admin_ssn, "admin")
   if revoke == "Token Dicabut":
      return redirect(url_for("login_admin"))
   else:
      return "Token Gagal Dicabut"

# Bagian User
@app.route("/", methods =["GET", "POST"])
def login():
   if request.method == "POST":
       # Baca input form HTML
       email = request.form.get("email")
       password = request.form.get("password")
       # Data yang dikirim ke API
       data = {'email':email, 'password':password, 'nomor_seri':getserial()}
       # Kirim POST ke server dan simpan sebagai object
       r = requests.post(url = "http://192.168.1.70:8000/api/login_station", data = data, headers = {"Accept": "application/json"})
       loads = r.json()
       messages = loads["data"]["token"]
       session["token"] = messages
       return messages
   return render_template("login.html")

if __name__ == "__main__":
   try:
      print("Bersii Refill Station - V1.0")
      print(" * Nomor Seri : " + getserial())
      app.run(host='192.168.1.90', port=80, debug=False)
      
   except KeyboardInterrupt:
      # Reset GPIO dan Token yang tersimpan
      GPIO.cleanup()	
      revoke = revoke_all()
   
