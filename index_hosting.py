'''
Bersii Refill Station - V1.0 / Desember 2022
'''
import requests
import json
import subprocess
import RPi.GPIO as GPIO
from flask import Flask, request, render_template, session, url_for, redirect

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
# Atur pin GPIO mesin refill
refill = 19
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
  
def getipaddress():
   ipaddr = subprocess.getoutput('hostname -I').strip()
   return ipaddr

def revoke_token(sessions, status):
   ssn_id = sessions.split('|')[0]
   # Data yang dikirim ke API
   serial = {'nomor_seri':getserial(), 'token_id':ssn_id}
   # Kirim POST ke server dan simpan sebagai object
   tokenizes_r = requests.post(url = "https://bersii.my.id/api/revoke_station", data = serial, headers = {"Accept": "application/json", "Authorization": "Bearer " + sessions})
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
   tokenizes_r = requests.post(url = "https://bersii.my.id/api/revoke_all", data = serial, headers = {"Accept": "application/json"})
   loads = tokenizes_r.json()
   message = loads["message"]
   if message == "Token Dicabut":
      session.pop("token", None)
      session.pop("token_admin", None)
   else:
      print("Token Gagal Dicabut")
   return message

# Bagian Admin
@app.route("/hardware_admin/<status>")
def hardware_admin1(status):
   if status == 'on':
      GPIO.output(refill, GPIO.HIGH)
      refillSts = GPIO.input(refill)
      templateData = {
         'hardware' : refillSts,
      }
      return render_template('hardware_admin.html', **templateData)
   elif status == 'off':
      GPIO.output(refill, GPIO.LOW)
      refillSts = GPIO.input(refill)
      templateData = {
         'hardware' : refillSts,
      }
      return render_template('hardware_admin.html', **templateData)

@app.route("/hardware_admin", defaults={'status': None})
def hardware_admin(status):
   if status is None :
      refillSts = GPIO.input(refill)
      templateData = {
         'hardware' : refillSts,
      }
      return render_template('hardware_admin.html', **templateData)
   
@app.route("/index_admin")
def index_admin():
   admin_ssn = session["token_admin"]
   # Data yang dikirim ke API
   data = {'nomor_seri':getserial()}
   # Kirim POST ke server dan simpan sebagai object
   rqs = requests.post(url = "https://bersii.my.id/api/station_stock", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
   rds = rqs.json()
   nama_produk = rds["data"][0]["nama_produk"]
   stok_produk = rds["data"][0]["stok"]
   harga_produk = rds["data"][0]["harga_produk"]
   templateData = {
      'nama_produk' : nama_produk,
      'stok_produk' : stok_produk,
      'harga_produk' : harga_produk,
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
      rqs = requests.post(url = "https://bersii.my.id/api/change_station_status", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
      rds = rqs.json()
      msg = rds["message"]
      return redirect(url_for("hwstatus_admin"))
      
   # Data yang dikirim ke API
   data = {'nomor_seri':getserial()}
   # Kirim POST ke server dan simpan sebagai object
   r = requests.post(url = "https://bersii.my.id/api/station_status", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
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
       r = requests.post(url = "https://bersii.my.id/api/login_station_admin", data = data, headers = {"Accept": "application/json"})
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
       r = requests.post(url = "https://bersii.my.id/api/login_station", data = data, headers = {"Accept": "application/json"})
       loads = r.json()
       user_id = loads["data"]["id"]
       nama = loads["data"]["nama"]
       email = loads["data"]["email"]
       telepon = loads["data"]["nomor_telepon"]
       alamat = loads["data"]["alamat"]
       token = loads["data"]["token"]
       # Ambil nama depan untuk panggilan
       all_words = nama.split()
       first_word = all_words[0]
       session["user_id"] = user_id
       session["nama"] = nama
       session["nama_depan"] = first_word
       session["email"] = email
       session["telepon"] = telepon
       session["alamat"] = alamat
       session["token"] = token
       return redirect(url_for("produk"))
   return render_template("login.html")

@app.route("/produk")
def produk():
   user_ssn = session["token"]
   userid = session["user_id"]
   # Data yang dikirim ke API
   data = {'nomor_seri':getserial()}
   # Kirim POST ke server dan simpan sebagai object
   rqs = requests.post(url = "https://bersii.my.id/api/station_stock", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + user_ssn})
   rds = rqs.json()
   id_produk = rds["data"][0]["id_produk"]
   nama_produk = rds["data"][0]["nama_produk"]
   stok_produk = rds["data"][0]["stok"]
   harga_produk = rds["data"][0]["harga_produk"]
   deskripsi_produk = rds["data"][0]["deskripsi_produk"]
   gambar_produk = rds["data"][0]["gambar_produk"]
   link_gambar = 'https://bersii.my.id/storage/upload/' + gambar_produk
   templateData = {
      'id_produk': id_produk,
      'nama_produk' : nama_produk,
      'stok_produk' : stok_produk,
      'harga_produk' : harga_produk,
      'deskripsi_produk' : deskripsi_produk,
      'gambar_produk': link_gambar,
   }
   return render_template("products.html", **templateData)
   
@app.route("/checkout", methods =["GET", "POST"])
def checkout():
   user_ssn = session["token"]
   userid = session["user_id"]
   nomor_seri = getserial()
   if request.method == "POST":
      id_produk = request.form.get('id_produk')
      jumlah_refill = request.form.get('jumlah_refill')
      harga_produk = request.form.get('harga_produk')
      # Data yang dikirim ke API
      data = {'nomor_seri':nomor_seri, 'jumlah_refill':jumlah_refill, 'id_produk':id_produk, 'id_user':userid, 'harga_produk':harga_produk}
      # Kirim POST ke server dan simpan sebagai object
      r = requests.post(url = "https://bersii.my.id/api/checkout_refill", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + user_ssn})
      loads = r.json()
      message = loads["message"]
      if message == "Transaksi Berhasil":
         return (message, 200)
      else:
         return (message, 500)
      
@app.route("/refillings", methods = ["GET", "POST"])
def refillings():
   if request.method == "POST":
      cond = request.form.get('condition')
      if cond == "Start":
         GPIO.output(refill, GPIO.HIGH)
         return ('Start', 200)
      else:
         GPIO.output(refill, GPIO.LOW)
         return ('Stop', 200)
      
if __name__ == "__main__":
   try:
      ip = getipaddress()
      print("Bersii Refill Station - V1.0")
      print(" * Nomor Seri : " + getserial())
      print(" * Nomor IP : " + ip)
      app.run(host = ip, port=443, debug=False, ssl_context='adhoc')
      
   except KeyboardInterrupt:
      # Reset GPIO dan Token yang tersimpan
      GPIO.cleanup()	
      revoke = revoke_all()
   
