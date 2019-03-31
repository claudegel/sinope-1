import logging
import requests
import json
import struct
import binascii
import socket
import sys
import pytz
from astral import Astral
import crc8
from datetime import datetime, timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.const import (CONF_API_KEY, CONF_ID,
    CONF_SCAN_INTERVAL, CONF_TIME_ZONE, CONF_LONGITUDE, CONF_LATITUDE)
from homeassistant.util import Throttle

#REQUIREMENTS = ['PY_Sinope==0.1.7']
REQUIREMENTS = ['crc8==0.0.5']

DOMAIN = 'sinope'
DATA_DOMAIN = 'data_' + DOMAIN
CONF_SERVER = 'server'
CONF_DK_KEY = 'dk_key'

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=300)

REQUESTS_TIMEOUT = 30

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_ID): cv.string,
        vol.Required(CONF_SERVER): cv.string,
        vol.Required(CONF_DK_KEY): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL):
            cv.time_period
    })
}, extra=vol.ALLOW_EXTRA)

def setup(hass, hass_config):
    """Set up sinope."""
    data = SinopeData(hass_config[DOMAIN])
    hass.data[DATA_DOMAIN] = data

    global SCAN_INTERVAL 
    SCAN_INTERVAL = hass_config[DOMAIN].get(CONF_SCAN_INTERVAL)
    _LOGGER.debug("Setting scan interval to: %s", SCAN_INTERVAL)
    
    discovery.load_platform(hass, 'climate', DOMAIN, {}, hass_config)
    discovery.load_platform(hass, 'light', DOMAIN, {}, hass_config)
    discovery.load_platform(hass, 'switch', DOMAIN, {}, hass_config)

    return True

class SinopeData:
    """Get the latest data and update the states."""

    def __init__(self, config):
        """Init the sinope data object."""
        api_key = config.get(CONF_API_KEY)
        api_id = config.get(CONF_ID)
        server = config.get(CONF_SERVER)
        dk_key = config.get(CONF_DK_KEY)
        city_name = "Montreal" # FIXME must come from configuration.yaml
        tz = config.get(CONF_TIME_ZONE)
        latitude = config.get(CONF_LATITUDE)
        longitude = config.get(CONF_LONGITUDE)
        self.sinope_client = SinopeClient(api_key, api_id, server, city_name, tz, latitude, longitude, dk_key)

    # Need some refactoring here concerning the class used to transport data
    # @Throttle(SCAN_INTERVAL)
    # def update(self):
    #     """Get the latest data from pysinope."""
    #     self.sinope_client.update()
    #     _LOGGER.debug("Sinope data updated successfully")



# According to HA: 
# https://developers.home-assistant.io/docs/en/creating_component_code_review.html
# "All API specific code has to be part of a third party library hosted on PyPi. 
# Home Assistant should only interact with objects and not make direct calls to the API."
# So all code below this line should eventually be integrated in a PyPi project.

class PySinopeError(Exception):
    pass

#import PY_Sinope

PORT = 4550

all_unit = "FFFFFFFF"
#sequential number to identify the current request. Could be any unique number that is different at each request
# could we use timestamp value ?
seq_num = 12345678 
seq = 0

# command type
data_read_command = "4002"
data_report_command = "4202"
data_write_command = "4402"

#thermostat data read
data_heat_level = "20020000" #0 to 100%
data_mode = "11020000" # off, manual, auto, bypass, away...
data_temperature = "03020000" #room temperature
data_setpoint = "08020000" #thermostat set point
data_away = "00070000"  #set device mode to away, 0=home, 2=away

#thermostat info read
data_display_format = "00090000" # 0 = celcius, 1 = fahrenheit
data_time_format = "01090000" # 0 = 24h, 1 = 12h
data_lock = "02090000" # 0 = unlock, 1 = lock
data_load = "000D0000" # 0-65519 watt, 1=1 watt, (2 bytes)
data_display2 = "30090000" # 0 = default setpoint, 1 = outdoor temp.
data_min_temp = "0A020000" # Minimum room setpoint, 5-30oC (2 bytes)
data_max_temp = "0B020000" # Maximum room setpoint, 5-30oC (2 bytes)
data_away_temp = "0C020000" # away room setpoint, 5-30oC (2 bytes)

# thermostat data report
data_outdoor_temperature = "04020000" #to show on thermostat, must be sent at least every hour
data_time = "00060000" #must be sent at least once a day or before write request for auto mode
data_date = "01060000" 
data_sunrise = "20060000" #must be sent onece a day
data_sunset = "21060000" #must be sent onece a day

# thermostat data write
data_early_start = "60080000"  #0=disabled, 1=enabled

# light and dimmer
data_light_intensity = "00100000"  # 0 to 100, off to on, 101 = last level
data_light_mode = "09100000"  # 1=manual, 2=auto, 3=random or away, 130= bypass auto
data_light_timer = "000F0000"   # time in minutes the light will stay on 0--255
data_light_event = "010F0000"  #0= no event sent, 1=timer active, 2= event sent for turn_on or turn_off

# Power control
data_power_intensity = "00100000"  # 0 to 100, off to on
data_power_mode = "09100000"  # 1=manual, 2=auto, 3=random or away, 130= bypass auto
data_power_connected = "000D0000" # actual load connected to the device
data_power_load = "020D0000" # load used by the device
data_power_event = "010F0000"  #0= no event sent, 1=timer active, 2= event sent for turn_on or turn_off
data_power_timer = "000F0000" # time in minutes the power will stay on 0--255

def crc_count(bufer):
    hash = crc8.crc8()
    hash.update(bufer)
    return hash.hexdigest()

def crc_check(bufer):
    hash = crc8.crc8()
    hash.update(bufer)
    if(hash.hexdigest() == "00"):
        return "00"
    return None

def get_dst(zone): # daylight saving time is on or not
    localtime = datetime.now(zone)
    if localtime.dst():
        return 128
    return 0

def set_date(zone):
    now = datetime.now(zone)
    day = int(now.strftime("%w"))-1
    if day == -1:
        day = 6
    w = bytearray(struct.pack('<i', day)[:1]).hex() #day of week, 0=monday converted to bytes
    d = bytearray(struct.pack('<i', int(now.strftime("%d")))[:1]).hex() #day of month converted to bytes
    m = bytearray(struct.pack('<i', int(now.strftime("%m")))[:1]).hex() #month converted to bytes
    y = bytearray(struct.pack('<i', int(now.strftime("%y")))[:1]).hex() #year converted to bytes
    date = '04'+w+d+m+y #xxwwddmmyy,  xx = length of data date = 04
    return date

def set_time(zone):
    now = datetime.now(zone)
    s = bytearray(struct.pack('<i', int(now.strftime("%S")))[:1]).hex() #second converted to bytes
    m = bytearray(struct.pack('<i', int(now.strftime("%M")))[:1]).hex() #minutes converted to bytes
    h = bytearray(struct.pack('<i', int(now.strftime("%H"))+get_dst(zone))[:1]).hex() #hours converted to bytes
    time = '03'+s+m+h #xxssmmhh  24hr, 16:09:00 pm, xx = length of data time = 03
    return time
  
def set_sun_time(city, zone, period): # period = sunrise or sunset
    a = Astral()
    city = a[city]
    sun = city.sun(date=datetime.now(zone), local=True)
    if period == "sunrise":
        now = sun['sunrise']
    else:
        now = sun['sunset']
    s = bytearray(struct.pack('<i', int(now.strftime("%S")))[:1]).hex() #second converted to bytes
    m = bytearray(struct.pack('<i', int(now.strftime("%M")))[:1]).hex() #minutes converted to bytes
    h = bytearray(struct.pack('<i', int(now.strftime("%H"))+get_dst(zone))[:1]).hex() #hours converted to bytes
    time = '03'+s+m+h #xxssmmhh  24hr, 16:09:00 pm, xx = length of data time = 03
    return time
  
def get_heat_level(data):
    sequence = data[12:]
    laseq = sequence[:8]
    dev = data[26:]
    deviceID = dev[:8]
    tc1 = data[46:]
    tc2 = tc1[:2]
    return int(float.fromhex(tc2))
  
def set_temperature(temp_celcius):
    temp = int(temp_celcius*100)
    return "02"+bytearray(struct.pack('<i', temp)[:2]).hex()
  
def get_temperature(data):
    sequence = data[12:]
    laseq = sequence[:8]
    dev = data[26:]
    deviceID = dev[:8]
    result = data[20:]
    status = result[:2]
    if status == "fc":
        return None # device didn't answer, wrong device
    else:  
        tc1 = data[46:]
        tc2 = tc1[:2]
        tc3 = data[48:]
        tc4 = tc3[:2]
        latemp = tc4+tc2
        return float.fromhex(latemp)*0.01
  
def to_celcius(temp):
    return round((temp-32)*0.5555, 2)

def from_celcius(temp):
    return round((temp+1.8)+32, 2)
  
def get_outside_temperature(key, latitude, longitude): #https://api.darksky.net/forecast/{your dark sky key}/{latitude},{logitude}
    r = requests.get('https://api.darksky.net/forecast/'+key+'/'+latitude+','+longitude+'?exclude=minutely,hourly,daily,alerts,flags')
    ledata =r.json()
    return to_celcius(float(json.dumps(ledata["currently"]["temperature"])))
    
def set_is_away(away): #0=home,2=away
    return "01"+bytearray(struct.pack('<i', away)[:1]).hex()
  
def get_is_away(data):
    sequence = data[12:]
    laseq = sequence[:8]
    dev = data[26:]
    deviceID = dev[:8]
    tc1 = data[46:]
    tc2 = tc1[:2]
    return int(float.fromhex(tc2))  

def set_mode(mode): #0=off,1=freeze protect,2=manual,3=auto,5=away
    return "01"+bytearray(struct.pack('<i', mode)[:1]).hex()
 
def get_mode(data):
    sequence = data[12:]
    laseq = sequence[:8]
    dev = data[26:]
    deviceID = dev[:8]
    tc1 = data[46:]
    tc2 = tc1[:2]
    return int(float.fromhex(tc2))
  
def set_intensity(num):
    return "01"+bytearray(struct.pack('<i', num)[:1]).hex()

def get_intensity(data):
    sequence = data[12:]
    laseq = sequence[:8]
    dev = data[26:]
    deviceID = dev[:8]
    tc1 = data[46:]
    tc2 = tc1[:2]
    return int(float.fromhex(tc2))
   
def get_power_load(data): # get power in watt use by the device
    sequence = data[12:]
    laseq = sequence[:8]
    dev = data[26:]
    deviceID = dev[:8]
    result = data[20:]
    status = result[:2]
    if status == "fc":
        return None # device didn't answer, wrong device
    else:     
        tc1 = data[46:]
        tc2 = tc1[:2]
        tc3 = data[48:]
        tc4 = tc3[:2]
        lepower = tc4+tc2
        return int(float.fromhex(lepower))
  
def set_light_event_on(num): #102 = light, 112 = dimmer
    b0 = "10"
    b1 = "00000000"
    b3 = "000000000000000000"
    if num == 102:
        b2 = "020200" #event on for light
    else:
        b2 = "020202" # event on for dimmer     
    return b0+b1+b2+b3

def set_light_timer_on(num): #102 = light, 112 = dimmer 
    b0 = "10"
    b1 = "00000000"
    b3 = "000000000000000000"
    if num == 102:
        b2 = "010100" #event on = timer start
    else:
        b2 = "010101" # event off = timer start  
    return b0+b1+b2+b3

def set_light_event_off(num): #102 = light, 112 = dimmer
    b0 = "10"
    b1 = "00000000"
    b3 = "000000000000000000"
    if num == 102:
        b2 = "010100" #all event = off except timer subscription (default)
    else:
        b2 = "000001" # dimmer
    return b0+b1+b2+b3

def get_light_event_state(data): #received event from light devices 00100000
    sequence = data[12:]
    laseq = sequence[:8]
    dev = data[26:]
    deviceID = dev[:8]
    tc1 = data[54:]
    tc2 = tc1[:8]
    return tc2 #int(float.fromhex(tc2))

def set_switch_event_on():
    b0 = "10"
    b1 = "0202"
    b2 = "0000000000000000000000000000"   
    return b0+b1+b2

def set_switch_timer_on():
    b0 = "10"
    b1 = "0101"
    b2 = "0000000000000000000000000000" 
    return b0+b1+b2

def set_switch_event_off():
    b0 = "10"
    b1 = "0000"
    b2 = "0000000000000000000000000000"
    return b0+b1+b2

def get_switch_event_state(data):
    sequence = data[12:]
    laseq = sequence[:8]
    dev = data[26:]
    deviceID = dev[:8]
    tc1 = data[46:]
    tc2 = tc1[:4]
    return  tc2 #int(float.fromhex(tc2))

def set_timer_length(num): # 0=desabled, 1 to 255 lenght on
    return "01"+bytearray(struct.pack('<i', num)[:1]).hex()
  
def get_timer_length(data): # 0=desabled, 1 to 255 lenght on
    sequence = data[12:]
    laseq = sequence[:8]
    dev = data[26:]
    deviceID = dev[:8]
    tc1 = data[46:]
    tc2 = tc1[:2]
    return int(float.fromhex(tc2))

def get_result(data): # check if data write was successfull, return True or False
    sequence = data[12:]
    laseq = sequence[:8]
    dev = data[26:]
    deviceID = dev[:8]
    tc1 = data[20:]
    tc2 = tc1[:2]
    if str(tc2) == "0a": #data read or write
        return True
    elif str(tc2) =="01": #data report
        return True
    return False
  
def error_info(bug,device):
    if bug == b'FF':
        _LOGGER.debug("in request for %s : Request failed.", device)
    elif bug == b'FE':
        _LOGGER.debug("in request for %s : Buffer full, retry later.", device)
    elif bug == b'FC':
        _LOGGER.debug("in request for %s : Device not responding.", device)
    elif bug == b'FB':
        _LOGGER.debug("in request for %s : Abort failed, request not found in queue.", device)
    elif bug == b'FA':
        _LOGGER.debug("in request for %s : Unknown device or destination deviceID is invalid or not a member of this network.", device)
    else:
        _LOGGER.debug("in request for %s : Unknown error.", device)
        
def send_request(self, *arg): #data
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (self._server, PORT)
    sock.connect(server_address)
    try:
        sock.sendall(login_request(self))
        if binascii.hexlify(sock.recv(1024)) == b'55000c001101000000030000032000009c': #login ok
            _LOGGER.debug("sinope login = ok")
            sock.sendall(arg[0])
            reply = sock.recv(1024)
            if crc_check(reply):  # receive acknoledge, check status and if we will receive more data
                seq_num = binascii.hexlify(reply)[12:20] #sequence id to link response to the correct request
                deviceid = binascii.hexlify(reply)[26:33]
                status = binascii.hexlify(reply)[20:22]
                more = binascii.hexlify(reply)[24:26] #check if we will receive other data
                if status == b'00': # request status = ok for read and write, we go on (read=00, report=01, write=00)
                    if more == b'01': #GT125 is sending another data response
                        datarec = sock.recv(1024) 
                        return datarec
                elif status == b'01': #status ok for data report
                    return reply
                else:       
                    error_info(status,deviceid)
                    return False
            return reply #unknown result send debug ?  
    finally:
        sock.close()
        
def login_request(self):
    login_data = "550012001001"+self._api_id+self._api_key
    login_crc = bytes.fromhex(crc_count(bytes.fromhex(login_data)))
    return bytes.fromhex(login_data)+login_crc
  
def get_seq(seq): # could be improuved
    if seq == 0:
        seq = seq_num
    seq += 1  
    return str(seq)  
  
def count_data(data):
    size = int(len(data)/2)
    return bytearray(struct.pack('<i', size)[:1]).hex()

def count_data_frame(data):
    size = int(len(data)/2)
    return bytearray(struct.pack('<i', size)[:2]).hex() 
  
def data_read_request(*arg): # command,unit_id,data_app
    head = "5500"
#    data_command = arg[0]
    data_seq = get_seq(seq)
    data_type = "00"
    data_res = "000000000000"
#    data_dest_id = unit_id
    app_data_size = "04"
    size = count_data_frame(arg[0]+data_seq+data_type+data_res+arg[1]+app_data_size+arg[2])
    data_frame = head+size+arg[0]+data_seq+data_type+data_res+arg[1]+app_data_size+arg[2]
    read_crc = bytes.fromhex(crc_count(bytes.fromhex(data_frame)))
    return bytes.fromhex(data_frame)+read_crc
  
def data_report_request(*arg): # data = size+time or size+temperature (command,unit_id,data_app,data)
    head = "5500"
#    data_command = arg[0]
    data_seq = get_seq(seq)
    data_type = "00"
    data_res = "000000000000"
#    data_dest_id = unit_id
    app_data_size = count_data(arg[2]+arg[3])
    size = count_data_frame(arg[0]+data_seq+data_type+data_res+arg[1]+app_data_size+arg[2]+arg[3])
    data_frame = head+size+arg[0]+data_seq+data_type+data_res+arg[1]+app_data_size+arg[2]+arg[3]
    read_crc = bytes.fromhex(crc_count(bytes.fromhex(data_frame)))
    return bytes.fromhex(data_frame)+read_crc
 
def data_write_request(*arg): # data = size+data to send (command,unit_id,data_app,data)
    head = "5500"
#    data_command = arg[0]
    data_seq = get_seq(seq)
    data_type = "00"
    data_res = "000000000000"
#    data_dest_id = unit_id
    app_data_size = count_data(arg[2]+arg[3])
    size = count_data_frame(arg[0]+data_seq+data_type+data_res+arg[1]+app_data_size+arg[2]+arg[3])
    data_frame = head+size+arg[0]+data_seq+data_type+data_res+arg[1]+app_data_size+arg[2]+arg[3]
    read_crc = bytes.fromhex(crc_count(bytes.fromhex(data_frame)))
    return bytes.fromhex(data_frame)+read_crc    

class SinopeClient(object):

    def __init__(self, api_key, api_id, server, city_name, tz, latitude, longitude, dk_key, timeout=REQUESTS_TIMEOUT):
        """Initialize the client object."""
        self._api_key = api_key
        self._api_id = api_id
        self._server = server
        self._city_name = city_name
        self._tz = tz
        self._latitude = latitude
        self._longitude = longitude
        self._dk_key = dk_key
        self.device_data = {}
        self.device_info = {}

# retreive data from devices        
        
    def get_climate_device_data(self, device_id):
        """Get device data."""
        # send requests
        try:
            temperature = get_temperature(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_temperature))).hex())
            setpoint = get_temperature(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_setpoint))).hex())
            heatlevel = get_heat_level(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_heat_level))).hex())
            mode = get_mode(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_mode))).hex())
            away = get_is_away(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_away))).hex())
        except OSError:
            raise PySinopeError("Cannot get climate data")
        # Prepare data
        self._device_data = {'setpoint': setpoint, 'mode': mode, 'alarm': 0, 'rssi': 0, 'temperature': temperature, 'heatLevel': heatlevel, 'away': away}
        return self._device_data

    def get_light_device_data(self, device_id):
        """Get device data."""
        # Prepare return
        data = {}
        # send requests
        try:
            intensity = get_intensity(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_light_intensity))).hex())
            mode = get_mode(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_light_mode))).hex())
        except OSError:
            raise PySinopeError("Cannot get light data")
        # Prepare data
        self._device_data = {'intensity': intensity, 'mode': mode, 'alarm': 0, 'rssi': 0}
        return self._device_data

    def get_switch_device_data(self, device_id):
        """Get device data."""
        # send requests
        try:
            intensity = get_intensity(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_power_intensity))).hex())
            mode = get_mode(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_power_mode))).hex())
            powerwatt = get_power_load(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_power_connected))).hex())
        except OSError:
            raise PySinopeError("Cannot get switch data")
        # Prepare data
        self._device_data = {'intensity': intensity, 'mode': mode, 'powerWatt': powerwatt, 'alarm': 0, 'rssi': 0}
        return self._device_data    
    
    def get_climate_device_info(self, device_id):
        """Get information for this device."""
        # send requests
        try:
            tempmax = get_temperature(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_max_temp))).hex())
            tempmin = get_temperature(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_min_temp))).hex())
            wattload = get_power_load(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_load))).hex())
            wattoveride = get_power_load(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_power_connected))).hex())
        except OSError:
            raise PySinopeError("Cannot get climate info")    
        # Prepare data
        self._device_info = {'active': 1, 'tempMax': tempmax, 'tempMin': tempmin, 'wattage': wattload, 'wattageOverride': wattoveride}
        return self._device_info

    def get_light_device_info(self, device_id):
        """Get information for this device."""
        # send requests
        try:
            timer = get_timer_length(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_light_timer))).hex())        except OSError:
        except OSError:
            raise PySinopeError("Cannot get light info")    
        # Prepare data
        self._device_info = {'active': 1, 'timer': timer}
        return self._device_info

    def get_switch_device_info(self, device_id):
        """Get information for this device."""
        # send requests
        try:
            wattload = get_power_load(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_power_load))).hex())
            timer = get_timer_length(bytearray(send_request(self, data_read_request(data_read_command,device_id,data_power_timer))).hex())
        except OSError:
            raise PySinopeError("Cannot get switch info")    
        # Prepare data
        self._device_info = {'active': 1, 'wattage': wattload, 'timer': timer}
        return self._device_info

    def set_brightness(self, device_id, brightness):
        """Set device intensity."""
        try:
            response = get_result(bytearray(send_request(self, data_write_request(data_write_command,device_id,data_light_intensity,set_intensity(brightness)))).hex())
        except OSError:
            raise PySinopeError("Cannot set device brightness")
        return response

    def send_time(self, device_id):
        """Send current time to device. it is required to set device mode to auto"""
        try:
            response = get_result(bytearray(send_request(self, data_write_request(data_write_command,device_id,data_time,set_time(self._tz)))).hex())
        except OSError:
            raise PySinopeError("Cannot send current time to device")
        return response
    
    def set_mode(self, device_id, device_type, mode):
        """Set device operation mode."""
        # prepare data
        try:
            if int(device_type) < 100:
                response = get_result(bytearray(send_request(data_write_request(self, data_write_command,device_id,data_mode,set_mode(mode)))).hex())
            else:
                response = get_result(bytearray(send_request(data_write_request(self, data_write_command,device_id,data_light_mode,set_mode(mode)))).hex())
        except OSError:
            raise PyNeviwebError("Cannot set device operation mode")
        return response
      
    def set_is_away(self, device_id, away):
        """Set device away mode."""
        try:
            if device_id == "all":
                device_id = "FFFFFFFF"
                response = get_result(bytearray(send_request(self, data_report_request(data_report_command,device_id,data_away,set_is_away(away)))).hex())
            else:    
                response = get_result(bytearray(send_request(self, data_write_request(data_write_command,device_id,data_away,set_is_away(away)))).hex())
        except OSError:
            raise PyNeviwebError("Cannot set device away mode")
        return response 
      
    def set_temperature(self, device_id, temperature):
        """Set device temperature."""
        try:
            response = get_result(bytearray(send_request(self, data_write_request(data_write_command,device_id,data_setpoint,set_temperature(temperature)))).hex())
        except OSError:
            raise PyNeviwebError("Cannot set device setpoint temperature")
        return response

    def set_timer(self, device_id, timer_length):
        """Set device timer length."""
        try:
            response = get_result(bytearray(send_request(self, data_write_request(data_write_command,device_id,data_light_timer,set_timer_length(timer_length)))).hex())
        except OSError:
            raise PyNeviwebError("Cannot set device timer length")
        return response 
    
    def set_report(self, device_id):
        """Set report to send data to each devices"""
        try:
            result = get_result(bytearray(send_request(self, data_report_request(data_report_command,device_id,data_time,set_time(self._tz)))).hex())
            if result == False:
                return result
            result = get_result(bytearray(send_request(self, data_report_request(data_report_command,device_id,data_date,set_date(self._tz)))).hex())
            if result == False:
                return result
            result = get_result(bytearray(send_request(self, data_report_request(data_report_command,device_id,data_sunrise,set_sun_time(self._city_name, self._tz, "sunrise")))).hex())
            if result == False:
                return result
            result = get_result(bytearray(send_request(self, data_report_request(data_report_command,device_id,data_sunset,set_sun_time(self._city_name, self._tz, "sunset")))).hex())
            if result == False:
                return result
            result = get_result(bytearray(send_request(self, data_report_request(data_report_command,device_id,data_outdoor_temperature,set_temperature(get_outside_temperature(self._dk_key, self._latitude, self._longitude))))).hex())
        except OSError:
            raise PyNeviwebError("Cannot send report to each devices")
        return result
