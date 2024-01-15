import subprocess
import schedule
import time
import json
import requests
import re
from pyngrok import ngrok

SAVE_FILE_PATH = "/home/hanvir/BersiiStation/urls.json"  # Replace with the desired path to save the JSON file

start_stts = "1"

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

def start_ngrok(port=6100, ssh=22):
    global start_stts
    ngrok.connect(port)
    ngrok.connect(ssh, "tcp")
    tunnels = str(ngrok.get_tunnels())
    https_match = re.search(r'"https://(.*?)"', tunnels)
    https_url = https_match.group(1)
    tcp_match = re.search(r'"tcp://(.*?)"', tunnels)
    tcp_url = tcp_match.group(1)
    if(start_stts == "1"):
        array = {
            "nomor_seri": getserial(),
            "http": "https://"+https_url,
            "ssh": tcp_url,
            "start": start_stts,
        }
    elif(start_stts == "0"):
        array = {
            "nomor_seri": getserial(),
            "http": "https://"+https_url,
            "ssh": tcp_url,
        }
    reqst = requests.post(url = "https://savon.bersii.my.id/api/station_public", data = array, headers = {"Accept": "application/json"})
    stts = {
        "nomor_seri": getserial(),
        "http": "https://"+https_url,
        "ssh": tcp_url,
        "status" : reqst
    }
    start_stts = "0"
    return stts

def reset_ngrok():
    print("Resetting Ngrok tunnels...")
    ngrok.kill()

    # Get Ngrok URLs
    ngrok = start_ngrok()

    # Save URLs to a JSON file
    urls = {"http": ngrok["http"], "ssh": ngrok["ssh"]}
    with open(SAVE_FILE_PATH, "w") as json_file:
        json.dump(urls, json_file, indent=2)

def main():
    # Get Ngrok URLs
    ngrok = start_ngrok()

    # Save URLs to a JSON file
    urls = {"http": ngrok["http"], "ssh": ngrok["ssh"]}
    with open(SAVE_FILE_PATH, "w") as json_file:
        json.dump(urls, json_file, indent=2)

    # Schedule tunnel reset every 2 hours
    schedule.every(2).hours.do(reset_ngrok)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        ngrok.kill()
        print("\nQuitting...")