#!/usr/bin/env python
import sys
import os
import subprocess
import random
import shelve
import signal
import time
import setup_indicator


# Commands
EXTERNAL_IP_CMD = ["wget", "http://ipinfo.io/ip", "-qO", "-"]
STUNNEL_CMD = ["nohup", "stunnel", "{}", "&"]
OPENVPN_CMD = ["nohup", "openvpn", "--config", "{}", "&"]
SYSTRAY_CMD = ["nohup", "python", "setup_indicator.py"]
GEOLOCATE_CMD = 'echo "Looking for self ip geolocation..." && curl -s ipinfo.io/"$(wget http://ipinfo.io/ip -qO -)" | egrep -w "city|region|country"'

AIRVPN_CONFIGS_PATH = os.getcwd()

AIRVPN_DNS_STRING = """nameserver 10.4.0.1\nnameserver 10.5.0.1"""
OPEN_DNS_STRING = """nameserver 127.0.1.1\nnameserver 208.67.222.222\nnameserver 208.67.220.220"""

"Make sure that the user is a sudoer"
if not os.geteuid() == 0:
  sys.exit("\nOnly root can run this script\n")

"""
This function turns on the vpn connection via SSL tunnel.
"""
def turn_on():
  initial_ip = subprocess.check_output(EXTERNAL_IP_CMD)
  print("##########################################################\n")
  print("#   Initial external IP: {}".format(initial_ip))
  print("#   Initial geolocation:")
  os.system(GEOLOCATE_CMD)
  print("##########################################################\n")
  print("")

  # Letting the user choose country from available countries configs
  countries_list = get_countries()
  country_code = raw_input("Which country would you like to exit from?\n({})\n".format(", ".join(countries_list)))
  config_path = random.choice(get_config_path(country_code.upper())) # picking random server from our desired country
  config_path = os.path.join(AIRVPN_CONFIGS_PATH, config_path)

  # Setting up the appropriate commands with the desired server config
  STUNNEL_CMD[2] = config_path+".ssl"
  OPENVPN_CMD[3] = config_path+".ovpn"
  print("ok, attempting to exit via {}".format(config_path))

  stunnel_pid = subprocess.Popen(STUNNEL_CMD,
                stdout=open('/tmp/stunnel.log', 'w'),
                stderr=open('/tmp/stunnel.log', 'a'),
                # stderr=open('/tmp/stunnel_err.log', 'a'),
                preexec_fn=os.setpgrp
                )

  # Waiting for the stunnel process to complete the init
  init_success = wait_for_process_init("/tmp/stunnel.log", "Configuration successful", "stunnel")

  openvpn_pid = subprocess.Popen(OPENVPN_CMD,
                  stdout=open('/tmp/openvpn.log', 'w'),
                  stderr=open('/tmp/openvpn_err.log', 'a'),
                  preexec_fn=os.setpgrp
                )

  print("pids - stunnel: {}, openvpn: {}".format(stunnel_pid.pid, openvpn_pid.pid))

  # Storing the pids of the background processes for shutdown later purpose
  pids_shelve = shelve.open("pids.db")
  pids_shelve["pids"] = {"stunnel_pid": stunnel_pid.pid,
                         "openvpn_pid": openvpn_pid.pid}
  pids_shelve.close()

  # Waiting for the openvpn process to complete the init
  init_success = wait_for_process_init("/tmp/openvpn.log", "Initialization Sequence Completed", "openvpn")

  # Validating the connection and setting system tray indicator
  try:
    final_ip = subprocess.check_output(EXTERNAL_IP_CMD)

    if initial_ip == final_ip:
      raise Exception("Same ip: {}".format(final_ip))

  except Exception as e:
    print("Error: {}".format(e))
    print("failed to change IP using airvpn")
    subprocess.Popen(['notify-send', "airvpn setup failed", "-t", "2000"])
    set_resolv_conf(False)
    pids_shelve = shelve.open("pids.db")
    pids_shelve["pids"] = []
    pids_shelve.close()
    os.kill(stunnel_pid.pid, signal.SIGTERM)
    os.kill(openvpn_pid.pid, signal.SIGTERM)
    exit()


  # Sucess. Changing the DNS at /etc/resolve.conf to airvpn DNS to avoid DNS leaks
  set_resolv_conf(True)

  # Calling the systray indicator setter with country code to appear on menu
  SYSSTRAY_CMD_COUNTRY = SYSTRAY_CMD + list("{}".format(country_code.upper()))
  systray_pid = subprocess.Popen(SYSSTRAY_CMD_COUNTRY,
                                 stdout=open('/tmp/systray.log', 'w'),
                                 stderr=open('/tmp/systray_err.log', 'a'),
                                 preexec_fn=os.setpgrp)

  # Storing the pid of the systray background processes for shutdown later purpose
  pids_shelve = shelve.open("pids.db")
  pids = pids_shelve["pids"]
  pids["systray_icon_pid"] = systray_pid.pid
  pids_shelve["pids"] = pids
  pids_shelve.close()

  # Notifying the user on the successful setup
  subprocess.Popen(['notify-send', "airvpn setup sucess", "-t", "5000"])
  print("##########################################################\n")
  print("Sucess! Final external IP: {}.".format(final_ip.strip("\n")))
  os.system(GEOLOCATE_CMD)
  print("##########################################################\n")
  print("")

"""
Turning off an active vpn+stunnel connection.
"""
def turn_off():
  # Fetching the pids from the shelve
  pids_shelve = shelve.open("pids.db")
  if pids_shelve.has_key("pids"):
    pids = pids_shelve["pids"]
  else:
    pids = None

  # Validating that the processes are running and if true, klling them and the systray icon
  stunnel_status, stunnel_pid = is_process_running("stunnel")
  openvpn_status, openvpn_pid = is_process_running("openvpn")

  try:
    assert len(pids) > 0 or stunnel_status or openvpn_status, "couldn't find any trace of airvpn running"
  except AssertionError as e:
    exit(repr(e.args[0]))

  if stunnel_status:
    os.kill(int(stunnel_pid), signal.SIGTERM)
  if openvpn_status:
    os.kill(int(openvpn_pid), signal.SIGTERM)
  if pids.has_key("systray_icon_pid"):
    os.kill(int(pids["systray_icon_pid"]), signal.SIGTERM)

  # Emptying the shelve
  pids_shelve["pids"] = []
  pids_shelve.close()

  # Changing the DNS at /etc/resolve.conf to opendns
  set_resolv_conf(False)

  # Notifying the user on the successful turning off
  subprocess.Popen(['notify-send', "airvpn is turned off", "-t", "5000"])
  print("\nTurned off Airvpn. Validating...")
  os.system(GEOLOCATE_CMD)
  print("")


########################
### Helper functions ###
########################

"""
This (blocking) function accepts file path, pattern, and (optional) process name.
It then wait for the last line of the file to match the pattern.
"""
def wait_for_process_init(fpath, pattern, process_name=None):
  last_line = tail(fpath, 1)
  if len(last_line) == 0: # wait a second, file is empty
    time.sleep(3)
    last_line = tail(fpath, 1)
  while not pattern in last_line[0]:
    last_line = tail(fpath, 1)
    if process_name:
      msg = "Waiting for {} to finish init".format(process_name)
      subprocess.Popen(['notify-send', msg, "-t", "2000"])
    else:
      subprocess.Popen(['notify-send', "Waiting for background process to finish init", "-t", "2000"])
    time.sleep(2)
  return True

"""
Checking if the proc_name is running
"""
def is_process_running(proc_name):
  try:
    _pid = subprocess.check_output(["pidof",proc_name])
  except subprocess.CalledProcessError:
    return False, None
  if _pid and len(_pid) > 0:
    return True, _pid.strip("\n")


"""
Returns a list of config files for given country_code
"""
def get_config_path(country_code):
  res = []
  for config_file in os.listdir(AIRVPN_CONFIGS_PATH):
    if "AirVPN_{}".format(country_code) in config_file and "SSL" in config_file:
      res.append(os.path.splitext(config_file)[0])
  if len(res) == 0:
    sys.exit("No config file for {} could be found. Exiting".format(country_code))
  return res

"""
Extract country codes from Airvpn config file names
"""
def get_countries():
  res = set()
  for config_file in os.listdir(AIRVPN_CONFIGS_PATH):
    if "AirVPN_" in config_file and "SSL" in config_file:
      # print "config: {}".format(config_file)
      country = config_file.split("AirVPN_")[1].split("-")[0]
      res.add(country)
  if len(res) == 0:
    sys.exit("No config files could be found. Exiting")

  return list(res)

"""
Changes the /etc/resolv.conf file to match opendns/airvpn dns.
@param state - True => Airvpn DNS. False => opendns
"""
def set_resolv_conf(state):
  with open("/etc/resolv.conf" , "w") as fout:
    if state:
      fout.write(AIRVPN_DNS_STRING)
    else:
      fout.write(OPEN_DNS_STRING)

"""
Returns the last lines of a given file.
Adapted from http://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail#answer-136368
"""
def tail(f, lines=20 ):
  total_lines_wanted = lines
  BLOCK_SIZE = 1024
  f = open(f, "r")
  f.seek(0, 2)
  block_end_byte = f.tell()
  lines_to_go = total_lines_wanted
  block_number = -1
  blocks = [] # blocks of size BLOCK_SIZE, in reverse order starting
              # from the end of the file
  while lines_to_go > 0 and block_end_byte > 0:
    if (block_end_byte - BLOCK_SIZE > 0):
      # read the last block we haven't yet read
      f.seek(block_number*BLOCK_SIZE, 2)
      blocks.append(f.read(BLOCK_SIZE))
    else:
      # file too small, start from begining
      f.seek(0,0)
      # only read what was not read
      blocks.append(f.read(block_end_byte))
    lines_found = blocks[-1].count('\n')
    lines_to_go -= lines_found
    block_end_byte -= BLOCK_SIZE
    block_number -= 1
  all_read_text = ''.join(reversed(blocks))
  f.close()
  return all_read_text.splitlines()[-total_lines_wanted:]

if __name__ == '__main__':
  if "on" in sys.argv:
    if is_process_running("stunnel")[0] or is_process_running("openvpn")[0]:
      exit("Airvpn is already activated")
    turn_on()
  elif "off" in sys.argv:
    if not is_process_running("stunnel")[0] and not is_process_running("openvpn")[0]:
      exit("Airvpn is already deactivated")
    turn_off()
  else:
    print("USAGE: airvpn_toggler.py <on/off>")
