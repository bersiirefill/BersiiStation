'''
Bersii Refill Station - V2.0 / Juni 2023
'''
import base64
import requests
import json
import time
import subprocess
import re
import RPi.GPIO as GPIO
import pusher
import threading
import queue
import usb.core
import usb.util
import sys
# import ngrok
from gpiozero import MotionSensor, DistanceSensor, OutputDevice, Device
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep
from pyngrok import conf, ngrok
from flask import Flask, request, jsonify, render_template, session, url_for, redirect
from flask_apscheduler import APScheduler
from datetime import datetime
from rpi_lcd import LCD
# from apscheduler.schedulers.background import BackgroundScheduler
app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
input_queue = queue.Queue()

# Inisialisasi LCD
lcd = LCD()

# Inisialisasi scheduler
scheduler = APScheduler()

# Factory
pigpiof = PiGPIOFactory()

# GPIO.setmode(GPIO.BCM)
# GPIO.setwarnings(False)
# Atur pin PIR sensor
pir = MotionSensor(19)
# Atur pin GPIO mesin refill
mesin_pin = 26
trigpin = 17
echopin = 27
refill = [mesin_pin, trigpin]
# Atur status mesin refill
refillSts = 0
# Atur pin GPIO mesin refill sebagai output

# for pin in refill:
#    GPIO.setup(pin, GPIO.OUT)
# # Atur pin GPIO Ultrasonic
# GPIO.setup(echopin, GPIO.IN)
# # Matikan mesin refill saat rpi menyala 
# GPIO.output(refill, GPIO.LOW)

# Solenoid
psln = 13
solenoid = OutputDevice(pin=psln, pin_factory=pigpiof)

# Kalibrasi
json_file_path = "config.json"

# Ngrok
ngrok_file_path = "urls.json"

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
   try:
      subprocess.check_output(['ip', 'link', 'show', 'wwan0'], stderr=subprocess.STDOUT)
      ipaddr = subprocess.getoutput('hostname -I | awk \'{print $2}\'').strip()  # Get IP from wwan0
   except subprocess.CalledProcessError:
      ipaddr = subprocess.getoutput('hostname -I | awk \'{print $1}\'').strip()  # Get IP from wlan0
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
      # rqs = requests.post(url = "https://bersii.my.id/api/station_stock", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
      # rds = rqs.json()
      # nama_produk = rds["data"]["nama_produk"]
      # stok_produk = rds["data"]["stok"]
      # harga_produk = rds["data"]["harga_produk"]
      templateData = {
         'nama_produk' : 'ABC',
         'stok_produk' : '5',
         'harga_produk' : '15000',
      }
      return render_template('index.html', **templateData)
   if "token_admin" in session:
         # Data yang dikirim ke API
         data = {'nomor_seri':getserial()}
         # Kirim POST ke server dan simpan sebagai object
         admin_ssn = session["token_admin"]
         # rqs = requests.post(url = "https://bersii.my.id/api/station_stock", data = data, headers = {"Accept": "application/json", "Authorization": "Bearer " + admin_ssn})
         # rds = rqs.json()
         # nama_produk = rds["data"]["nama_produk"]
         # stok_produk = rds["data"]["stok"]
         # harga_produk = rds["data"]["harga_produk"]
         templateData = {
            'nama_produk' : 'Marjan',
            'stok_produk' : '5',
            'harga_produk' : '20000',
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

   # pulse_start = 0
   # pulse_end = 0
   # pulse_duration = 0
   # # Cek jarak antara air dan sensor ultrasonik
   # GPIO.output(trigpin, GPIO.HIGH)
   # time.sleep(0.00001)
   # GPIO.output(trigpin, GPIO.LOW)
   # while GPIO.input(echopin) == GPIO.LOW:
   #    pulse_start = time.time()
   # while GPIO.input(echopin) == GPIO.HIGH:
   #    pulse_end = time.time()
   # pulse_duration = pulse_end - pulse_start
   # distance = pulse_duration * 17474

   ultrasonic_sensor = DistanceSensor(echo=echopin, trigger=trigpin, pin_factory=pigpiof)
   distance = ultrasonic_sensor.distance * 100

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
   ultrasonic_sensor.close()
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
   refill_output = OutputDevice(pin=mesin_pin, pin_factory=pigpiof)
   if status == 'on':
      # GPIO.output(refill, GPIO.HIGH)
      # refillSts = GPIO.input(refill)
      refill_output.on()
   elif status == 'off':
      # GPIO.output(refill, GPIO.LOW)
      # refillSts = GPIO.input(refill)
      refill_output.off()
   refill_output.close()
   return status

@app.route("/kalibrasi", methods=["POST"])
def kalibrasi():

   # pulse_start = 0
   # pulse_end = 0
   # pulse_duration = 0
   # # Cek jarak antara air dan sensor ultrasonik
   # GPIO.output(trigpin, GPIO.HIGH)
   # time.sleep(0.00001)
   # GPIO.output(trigpin, GPIO.LOW)
   # while GPIO.input(echopin) == GPIO.LOW:
   #    pulse_start = time.time()
   # while GPIO.input(echopin) == GPIO.HIGH:
   #    pulse_end = time.time()
   # pulse_duration = pulse_end - pulse_start
   # distance = pulse_duration * 17474

   ultrasonic_sensor = DistanceSensor(echo=echopin, trigger=trigpin, pin_factory=pigpiof)
   distance = ultrasonic_sensor.distance * 100
   pulse_duration = ultrasonic_sensor.pulse_duration

   templateData = {
      'durasi' : round(pulse_duration),
      'jarak' : round(distance),
   }

   ultrasonic_sensor.close()
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
   # pulse_start = 0
   # pulse_end = 0
   # pulse_duration = 0
   # # Cek jarak antara air dan sensor ultrasonik
   # GPIO.output(trigpin, GPIO.HIGH)
   # time.sleep(0.00001)
   # GPIO.output(trigpin, GPIO.LOW)
   # while GPIO.input(echopin) == GPIO.LOW:
   #    pulse_start = time.time()
   # while GPIO.input(echopin) == GPIO.HIGH:
   #    pulse_end = time.time()
   # pulse_duration = pulse_end - pulse_start
   # distance = pulse_duration * 17474

   ultrasonic_sensor = DistanceSensor(echo=echopin, trigger=trigpin, pin_factory=pigpiof)
   distance = ultrasonic_sensor.distance * 100
   
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
   ultrasonic_sensor.close()

def set_ngrok():
   with open(ngrok_file_path, 'r') as file:
      data = json.load(file)
   https_url = data.get('http')
   tcp_url = data.get('ssh')
   stts = {
      "nomor_seri": getserial(),
      "http": https_url,
      "ssh": tcp_url,
   }
   return stts

def scroll_text(text, delay=0.5):
   length = len(text)
   text = text + ' ' * length
   for i in range(len(text) - length + 1):
      lcd.text(text[i:i+length], 1)
      sleep(delay)

def start_flask():
   ip = getipaddress()
   link = set_ngrok()
   print("Bersii Refill Station - V2.0")
   print(" * Nomor Seri : " + getserial())
   print(" * Nomor IP : " + ip)
   http = link["http"]
   ssh = link["ssh"]
   print(f" * URL HTTP Dinamis : {http}")
   print(f" * URL SSH Dinamis : {ssh}")
   # app.run(host='0.0.0.0', port=6100, debug=False, ssl_context='adhoc')
   lcd.text("Bersii Refill", 1)
   lcd.text("Station - V2.0", 2)
   sleep(2)
   lcd.clear()
   lcd.text("Nomor Seri:", 1)
   lcd.text(getserial(), 2)
   sleep(2)
   lcd.clear()
   lcd.text("Nomor IP:", 1)
   lcd.text(ip, 2)
   sleep(2)
   lcd.clear()

   lcd.text("URL HTTP:", 1)
   sleep(2)
   scroll_text(http)
   sleep(2)
   lcd.clear()

   lcd.text("URL SSH:", 1)
   sleep(2)
   scroll_text(ssh)
   sleep(2)
   lcd.clear()
   
   lcd.text("Sistem Siap", 1)
   sleep(2)
   lcd.clear()

   sleep(2)
   lcd.text("Bersii Refill", 1)
   lcd.text("Ketik jml refill", 2)

   scheduler.init_app(app)
   scheduler.start()
   app.run(host='0.0.0.0', port=6100, debug=False, ssl_context='adhoc')

def set_pir():
    if pir.wait_for_motion():
        return True 
    return False

# USB Keyboard input handling
def monitor_usb_keyboard():
   solenoid.on()
   key_mapping = {
      89: '1',
      90: '2',
      91: '3',
      92: '4',
      93: '5',
      94: '6',
      95: '7',
      96: '8',
      97: '9',
      98: '0',
      99: '.',
      88: 'enter',
      42: 'delete',
   }

   refill_output = OutputDevice(pin=mesin_pin, pin_factory=pigpiof)

   fp = open('/dev/hidraw0', 'rb')
   while True:
      buffer = fp.read(8)
      for c in buffer:
         if c > 0:
            if c in key_mapping:
               char = key_mapping[c]
               if char == 'enter':
                  user_input = ''.join(input_queue.queue)
                  if not user_input or user_input == '0':
                     break
                  input_queue.queue.clear()
                  lcd.clear()
                  lcd.text("Letakkan Botol", 1)
                  lcd.text("di bawah", 2)
                  # Cek apakah ada botol di bawah dengan PIR
                  rfl = set_pir()
                  while rfl == False:
                     sleep(0.1)
                     rfl = set_pir()
                     if rfl == True:
                        break
                  lcd.clear()

                  # Kalau pakai sensor beneran
                  # lcd.text(f"Mengisi: {user_input} ltr", 1)
                  # liter = 10
                  # flin = float(user_input)
                  # stk = 0
                  # while stk < flin:
                  #    lcd.text(f"{stk} liter", 2)
                  #    GPIO.output(refill, GPIO.HIGH)
                  #    liter = liter - stk
                  #    if(stk == flin):
                  #       break
                  # GPIO.output(refill, GPIO.LOW)

                  for i in range(5, 0, -1):
                     lcd.text("Mengisi dalam : ", 1)
                     lcd.text(f"{i}", 2)
                     sleep(0.5)
                     if i == 0:
                        break
                  
                  # Liter sementara (kalau sudah pakai HCSR04 baru diwhile)
                  lcd.text(f"Mengisi: {user_input} ltr", 1)
                  liter = 10
                  flin = float(user_input)
                  for stk in [i / 10.0 for i in range(int((flin * 10) + 1))]:
                     lcd.text(f"{stk:.1f} liter", 2)
                     # GPIO.output(refill, GPIO.HIGH)
                     refill_output.on()
                     solenoid.off()
                     liter = float(liter) - stk
                     sleep(1)  # Adjust the sleep duration as needed
                     if stk == flin:
                        break
                  # GPIO.output(refill, GPIO.LOW)
                  refill_output.off()
                  solenoid.on()
                  lcd.text("Pengisian telah", 1)
                  lcd.text("selesai", 2)
                  # refill_output.close()
                  sleep(5)
                  lcd.clear()
                  lcd.text("Bersii Refill", 1)
                  lcd.text("Ketik jml refill", 2)

               elif char == 'delete':
                  if not input_queue.empty():
                     queue_list = list(input_queue.queue)
                     if queue_list:
                        queue_list.pop()
                        input_queue.queue = queue_list
                        lcd.text('Jumlah Pengisian (l)', 1)
                        lcd.text(''.join(input_queue.queue), 2)
               else:
                  input_queue.put(char)
                  lcd.text('Jumlah Pengisian (l)', 1)
                  lcd.text(''.join(input_queue.queue), 2)
            else:
               lcd.text('Jumlah Pengisian (l)', 1)
               lcd.text(f"Unknown key: {c}", 2)


if __name__ == "__main__":
   try:

      # Thread for Flask app
      flask_thread = threading.Thread(target=start_flask)
      flask_thread.daemon = True
      flask_thread.start()

      # Check if the Flask & USB thread is alive
      while not flask_thread.is_alive():
         sleep(0.1)
      print("Flask thread is now running.")

      sleep(5)

      usb_thread = threading.Thread(target=monitor_usb_keyboard)
      usb_thread.daemon = True
      usb_thread.start()

      while not usb_thread.is_alive():
         sleep(0.1)
      print("USB thread is now running.")

      while True:
         sleep(1)

      # while True:
      #    ultrasonic_sensor = DistanceSensor(echo=echopin, trigger=trigpin, pin_factory=pigpiof)
      #    distance = ultrasonic_sensor.distance * 100
      #    print(distance)
      #    ultrasonic_sensor.close()
      #    sleep(1)
      
   except KeyboardInterrupt:
      lcd.clear()
      solenoid.off()
      # Reset GPIO dan Token yang tersimpan
      revoke = revoke_all()
      # GPIO.cleanup()	
