'''
Bersii Refill Station - V2.0 / Juni 2023
'''
import base64
import requests
import json
import time
import subprocess
import RPi.GPIO as GPIO
import pusher
from flask import Flask, request, jsonify, render_template, session, url_for, redirect
from flask_apscheduler import APScheduler
from datetime import datetime
# from apscheduler.schedulers.background import BackgroundScheduler
app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Inisialisasi scheduler
scheduler = APScheduler()

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
# Atur pin GPIO mesin refill
mesin_pin = 26
trigpin = 17
echopin = 27
refill = [mesin_pin, trigpin]
# Atur status mesin refill
refillSts = 0
# Atur pin GPIO mesin refill sebagai output
for pin in refill:
    GPIO.setup(pin, GPIO.OUT)
# Atur pin GPIO Ultrasonic
GPIO.setup(echopin, GPIO.IN)
# Matikan mesin refill saat rpi menyala 
GPIO.output(refill, GPIO.LOW)

# Kalibrasi
json_file_path = "config.json"

# Pusher Notification
pusher_client = pusher.Pusher(
  app_id='1722594',
  key='47654494660254b1d35f',
  secret='e4372837d33353c1a97c',
  cluster='ap1',
  ssl=True
)

# Kirim notifikasi
def sendpusher(channelset, eventset, data = {}):
   title = data["title"]
   body = data["body"]
   channel = channelset
   event = eventset
   array = {
      'title': title,
      'body': body,
   }
   operation = pusher_client.trigger(channel, event, array)
   return operation

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

def revoke_token(sessions):
   ssn_id = sessions.split('|')[0]
   # Data yang dikirim ke API
   serial = {'nomor_seri':getserial(), 'token_id':ssn_id}
   # Kirim POST ke server dan simpan sebagai object
   tokenizes_r = requests.post(url = "https://bersii.my.id/api/revoke_station", data = serial, headers = {"Accept": "application/json", "Authorization": "Bearer " + sessions})
   loads = tokenizes_r.json()
   message = loads["message"]
   if message == "Token Dicabut":
      session.pop("id_admin", None)
      session.pop("nama_admin", None)
      session.pop("email_admin", None)
      session.pop("jabatan_admin", None)
      session.pop("token_admin", None)
      session.clear()
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
      session.pop("id_admin", None)
      session.pop("nama_admin", None)
      session.pop("email_admin", None)
      session.pop("jabatan_admin", None)
      session.pop("token_admin", None)
      session.clear()
      print("Semua Token Dicabut")
   else:
      print("Token Gagal Dicabut")
   return message

@app.route("/logout", methods =["GET", "POST"])
def logout():
   admin_ssn = session["token_admin"]
   revoke = revoke_token(admin_ssn)
   return revoke

@app.route("/")
def start():
   return redirect(url_for("master"))

@app.route("/index", methods =["GET", "POST"])
def master():
   admin_ssn = None
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
      session["nomor_seri"] = getserial()
      # Render halaman dashboard
      admin_ssn = session["token_admin"]
      # Data yang dikirim ke API
      data = {'nomor_seri':getserial()}
      # Kirim POST ke server dan simpan sebagai object
      rqs = requests.post(url = "https://bersii.my.id/api/station_stock", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
      rds = rqs.json()
      nama_produk = rds["data"]["nama_produk"]
      stok_produk = rds["data"]["stok"]
      harga_produk = rds["data"]["harga_produk"]
      templateData = {
         'nama_produk' : nama_produk,
         'stok_produk' : stok_produk,
         'harga_produk' : harga_produk,
      }
      return render_template('index.html', **templateData)
   if "token_admin" in session:
         # Data yang dikirim ke API
         data = {'nomor_seri':getserial()}
         # Kirim POST ke server dan simpan sebagai object
         admin_ssn = session["token_admin"]
         rqs = requests.post(url = "https://bersii.my.id/api/station_stock", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
         rds = rqs.json()
         nama_produk = rds["data"]["nama_produk"]
         stok_produk = rds["data"]["stok"]
         harga_produk = rds["data"]["harga_produk"]
         templateData = {
            'nama_produk' : nama_produk,
            'stok_produk' : stok_produk,
            'harga_produk' : harga_produk,
         }
         return render_template('index.html', **templateData)
   else:
      return render_template("login.html")   
   
# BATAS MAIN CONTROLLER 

# Dashboard

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
   if request.method == 'POST' or request.method == 'GET':
      return render_template('dashboard/dashboard.html')
   
@app.route('/produksi', methods=['GET', 'POST'])
def produksi():
   if request.method == 'POST' or request.method == 'GET':
      return render_template('dashboard/produksi.html')

@app.route("/realtime_stok", methods=["POST"])
def realtime_stok():
   pulse_start = 0
   pulse_end = 0
   pulse_duration = 0
   # Cek jarak antara air dan sensor ultrasonik
   GPIO.output(trigpin, GPIO.HIGH)
   time.sleep(0.00001)
   GPIO.output(trigpin, GPIO.LOW)
   while GPIO.input(echopin) == GPIO.LOW:
      pulse_start = time.time()
   while GPIO.input(echopin) == GPIO.HIGH:
      pulse_end = time.time()
   pulse_duration = pulse_end - pulse_start
   distance = pulse_duration * 17474
   # Atur isi default tangki
   stok_produk = 0
   if(distance > 26):
      stok_produk = 0
   elif(distance < 26 and distance > 13):
      stok_produk = 5
   else:
      stok_produk = 10
   admin_ssn = session["token_admin"]
   # Data yang dikirim ke API
   data = {
      'nomor_seri':getserial(),
      'stok_produk':stok_produk,
      'jarak_pantul':distance,
   }
   # Kirim POST ke server dan simpan sebagai object
   rqs = requests.post(url = "https://bersii.my.id/api/cron_stok", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
   rds = rqs.json()
   # print(rds)
   stok_produkr = rds["data"]["stok"]
   nama_produkr = rds["data"]["nama_produk"]
   # Cek sinkron
   rst = 0
   if(stok_produkr == stok_produk):
      rst = stok_produkr
   else:
      rst = stok_produk
   templateData = {
      'stok_produk' : rst,
      'jarak' : round(distance),
      'nama_produk' : nama_produkr,
   }
   return json.dumps(templateData)

# Pembukuan

@app.route('/pembukuan', methods=['GET', 'POST'])
def pembukuan():
   if request.method == 'POST' or request.method == 'GET':
        return render_template('pembukuan/pembukuan.html')

# Konfigurasi

@app.route('/konfigurasi', methods=['GET', 'POST'])
def konfigurasi():
   if request.method == 'POST' or request.method == 'GET':
         admin_ssn = session["token_admin"]
         # Data yang dikirim ke API
         data = {'nomor_seri':getserial()}
         # Kirim POST ke server dan simpan sebagai object
         r = requests.post(url = "https://bersii.my.id/api/station_status", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
         loads = r.json()
         # Baca Config
         with open(json_file_path, 'r') as file:
            data = json.load(file)
         kedalaman = data.get('kedalaman_max_cm')
         kapasitas = data.get('kapasitas_max_liter')
         konversi = data.get('konversi')
         templateData = {
            'nomor_seri' : getserial(),
            'latitude' : loads["data"]["latitude"],
            'longitude' : loads["data"]["longitude"],
            'status_mesin' : loads["data"]["status_mesin"],
            'alamat' : loads["data"]["alamat"],
            'update_terakhir' : loads["data"]["update_terakhir"].split(".")[0],
            'kedalaman' : kedalaman,
            'kapasitas' : kapasitas,
            'konversi' : konversi,
         }
         return render_template('konfigurasi/konfigurasi.html', **templateData)
   
@app.route('/save_konfigurasi', methods=['POST'])
def save_konfigurasi():
   admin_ssn = session["token_admin"]
   status = request.form.get("status")
   # Data yang dikirim ke API
   data = {'nomor_seri':getserial(), 'status':status}
   # Kirim POST ke server dan simpan sebagai object
   rqs = requests.post(url = "https://bersii.my.id/api/change_station_status", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
   rds = rqs.json()
   msg = rds["message"]
   return msg

@app.route("/hardware/<status>")
def hardware(status):
   if status == 'on':
      GPIO.output(refill, GPIO.HIGH)
      refillSts = GPIO.input(refill)
      return refillSts
   elif status == 'off':
      GPIO.output(refill, GPIO.LOW)
      refillSts = GPIO.input(refill)
      return refillSts

@app.route("/kalibrasi", methods=["POST"])
def kalibrasi():
   pulse_start = 0
   pulse_end = 0
   pulse_duration = 0
   # Cek jarak antara air dan sensor ultrasonik
   GPIO.output(trigpin, GPIO.HIGH)
   time.sleep(0.00001)
   GPIO.output(trigpin, GPIO.LOW)
   while GPIO.input(echopin) == GPIO.LOW:
      pulse_start = time.time()
   while GPIO.input(echopin) == GPIO.HIGH:
      pulse_end = time.time()
   pulse_duration = pulse_end - pulse_start
   distance = pulse_duration * 17474
   templateData = {
      'durasi' : round(pulse_duration),
      'jarak' : round(distance),
   }
   return json.dumps(templateData)

@app.route("/simpan_kalibrasi", methods=["POST"])
def simpan_kalibrasi():
   try:
      # Baca input form HTML
      kedalaman = request.form.get("kedalaman")
      kapasitas = request.form.get("kapasitas")
      konversi = request.form.get("konversi")
      data = {
         "kedalaman_max_cm": kedalaman,
         "kapasitas_max_liter": kapasitas,
         "konversi": konversi
      }

      # Save the data to the JSON file
      with open(json_file_path, 'w') as file:
         json.dump(data, file)

      return jsonify({"message": "Data successfully saved."}), 200

   except Exception as e:
      return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route("/notify", methods =["POST"])
def notify():
   title = request.form.get("title")
   body = request.form.get("body")
   data = {
      'title': title,
      'body': body,
   }
   operation = sendpusher('notifications', 'admin-notif', data)
   return operation

# Job terjadwal via cron & interval

# @scheduler.task('cron', id='cron_stok', minute='5', hour='6')


@scheduler.task('interval', id='cron_stok', seconds=60)
def cron_stok():
   pulse_start = 0
   pulse_end = 0
   pulse_duration = 0
   # Cek jarak antara air dan sensor ultrasonik
   GPIO.output(trigpin, GPIO.HIGH)
   time.sleep(0.00001)
   GPIO.output(trigpin, GPIO.LOW)
   while GPIO.input(echopin) == GPIO.LOW:
      pulse_start = time.time()
   while GPIO.input(echopin) == GPIO.HIGH:
      pulse_end = time.time()
   pulse_duration = pulse_end - pulse_start
   distance = pulse_duration * 17474
   # Atur isi default tangki
   stok_produk = 0
   if(distance > 26):
      stok_produk = 0
   elif(distance < 26 and distance > 13):
      stok_produk = 5
   else:
      stok_produk = 10
   # Data yang dikirim ke API
   data = {
      'nomor_seri':getserial(),
      'stok_produk':stok_produk,
      'jarak_pantul':distance,
   }
   # Kirim POST ke server dan simpan sebagai object
   rqs = requests.post(url = "https://bersii.my.id/api/cron_stok", data = data, headers = {"Accept": "application/json"})
   rds = rqs.json()
   current_datetime = datetime.now()
   # print('Isi : ' + str(data["stok_produk"]) + ' / Jarak Pantul : ' + str(data["distance"]) + ' ------ ' + current_datetime.strftime("%Y-%m-%d %H:%M:%S")) 
   status = rds["status"]
   message = rds["message"]
   nama_produk = rds["data"]["nama_produk"]
   # Pusher
   data = {
      'title': 'Stok',
      'body': {
         'stok': stok_produk,
         'jarak': distance,
         'nama_produk': nama_produk,
      },
   }
   operation = sendpusher('stok-'+getserial(), 'station-stok', data)
   print(' * ' + str(message) + ' --- Stok : ' + str(stok_produk) + ' / Jarak Pantul : ' + str(distance) + ' --- ' + current_datetime.strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
   try:
      ip = getipaddress()
      print("Bersii Refill Station - V2.0")
      print(" * Nomor Seri : " + getserial())
      print(" * Nomor IP : " + ip)
      scheduler.init_app(app)
      scheduler.start()
      app.run(host=ip, port=6100, debug=False, ssl_context='adhoc')
      
   except KeyboardInterrupt:
      # Reset GPIO dan Token yang tersimpan
      revoke = revoke_all()
      GPIO.cleanup()	
      
