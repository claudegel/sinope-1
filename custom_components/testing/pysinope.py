import struct
import binascii
import socket
import crc8
from datetime import datetime
import pytz
from astral import Astral

### data that will come from HA
SERVER = "192.168.xxx.xxx"  # ip address of the GT125

# write key here once you get it with the ping request
Api_Key = None

# this is the ID printed on your GT125 but you need to write it reversly.
# ex. ID: 0123 4567 89AB CDEF => EFCDAB8967452301
Api_ID = "xxxxxxxxxxxxxxxx"

PORT = 4550

city_name = "Montreal"  # change it for your location
tz = pytz.timezone("America/New_York")  # change it for your location
# sequential number to identify the current request. Could be any unique number that is different at each request
# could we use timestamp value ?
seq_num = 12345678
seq = 0

# command type
data_read_command = "4002"
data_report_command = "4202"
data_write_command = "4402"

# device identification
# all_unit = "FFFFFFFF" #for data_report_command only, broadcasted to all devices
# device_id = "2e320100" # receive from GT125 device link report. Only for test purpose. Will be sent by HA

# thermostat data read
data_heat_level = "20020000"  # 0 to 100%
data_mode = "11020000"  # off, manual, auto, bypass, away...
data_temperature = "03020000"  # room temperature
data_setpoint = "08020000"  # thermostat set point
data_away = "00070000"  # set device mode to away, 0=none, 2=away

# thermostat info read
data_display_format = "00090000"  # 0 = celcius, 1 = fahrenheit
data_time_format = "01090000"  # 0 = 24h, 1 = 12h
data_lock = "02090000"  # 0 = unlock, 1 = lock
data_load = "000D0000"  # 0-65519 watt, 1=1 watt, (2 bytes)
data_display2 = "30090000"  # 0 = default setpoint, 1 = outdoor temp.
data_min_temp = "0A020000"  # Minimum room setpoint, 5-30oC (2 bytes)
data_max_temp = "0B020000"  # Maximum room setpoint, 5-30oC (2 bytes)
data_away_temp = "0C020000"  # away room setpoint, 5-30oC (2 bytes)

# thermostat data report
data_outdoor_temperature = (
    "04020000"  # to show on thermostat, must be sent at least every hour
)
data_time = (
    "00060000"  # must be sent at least once a day or before write request for auto mode
)
data_date = "01060000"
data_sunrise = "20060000"  # must be sent onece a day
data_sunset = "21060000"  # must be sent onece a day

# thermostat data write
data_early_start = "60080000"  # 0=disabled, 1=enabled

# light and dimmer
data_light_intensity = "00100000"  # 0 to 100, off to on, 101 = last level
data_light_mode = "09100000"  # 1=manual, 2=auto, 3=random or away, 130= bypass auto
data_light_timer = "000F0000"  # time in minutes the light will stay on 0--255
data_light_event = "010F0000"  # 0= no event sent, 1=timer active, 2= event sent for turn_on or turn_off

# Power control
data_power_intensity = "00100000"  # 0 to 100, off to on
data_power_mode = "09100000"  # 1=manual, 2=auto, 3=random or away, 130= bypass auto
data_power_connected = "000D0000"  # actual load connected to the device
data_power_load = "020D0000"  # load used by the device
data_power_event = "010F0000"  # 0 = no event sent, 1 = timer active, 2 = event sent for turn_on or turn_off
data_power_timer = "000F0000"  # time in minutes the power will stay on 0--255


def crc_count(bufer):
    hash = crc8.crc8()
    hash.update(bufer)
    return hash.hexdigest()


def crc_check(bufer):
    hash = crc8.crc8()
    hash.update(bufer)
    if hash.hexdigest() == "00":
        return "00"
    return None


def get_dst():  # daylight saving time is on or not
    localtime = datetime.now(tz)
    if localtime.dst():
        return 128
    return 0


def set_date():
    now = datetime.now(tz)
    day = int(now.strftime("%w")) - 1
    if day == -1:
        day = 6
    w = bytearray(
        struct.pack("<i", day)[:1]
    ).hex()  # day of week, 0=monday converted to bytes
    d = bytearray(
        struct.pack("<i", int(now.strftime("%d")))[:1]
    ).hex()  # day of month converted to bytes
    m = bytearray(
        struct.pack("<i", int(now.strftime("%m")))[:1]
    ).hex()  # month converted to bytes
    y = bytearray(
        struct.pack("<i", int(now.strftime("%y")))[:1]
    ).hex()  # year converted to bytes
    date = "04" + w + d + m + y  # xxwwddmmyy,  xx = lenght of data date = 04
    return date


def set_time():
    now = datetime.now(tz)
    s = bytearray(
        struct.pack("<i", int(now.strftime("%S")))[:1]
    ).hex()  # second converted to bytes
    m = bytearray(
        struct.pack("<i", int(now.strftime("%M")))[:1]
    ).hex()  # minutes converted to bytes
    h = bytearray(
        struct.pack("<i", int(now.strftime("%H")) + get_dst())[:1]
    ).hex()  # hours converted to bytes
    time = (
        "03" + s + m + h
    )  # xxssmmhh  24hr, 16:09:00 pm, xx = lenght of data time = 03
    return time


def set_sun_time(period):  # period = sunrise or sunset
    a = Astral()
    city = a[city_name]
    sun = city.sun(date=datetime.now(tz), local=True)
    if period == "sunrise":
        now = sun["sunrise"]
    else:
        now = sun["sunset"]

    s = bytearray(
        struct.pack("<i", int(now.strftime("%S")))[:1]
    ).hex()  # second converted to bytes
    m = bytearray(
        struct.pack("<i", int(now.strftime("%M")))[:1]
    ).hex()  # minutes converted to bytes
    h = bytearray(
        struct.pack("<i", int(now.strftime("%H")) + get_dst())[:1]
    ).hex()  # hours converted to bytes
    time = (
        "03" + s + m + h
    )  # xxssmmhh  24hr, 16:09:00 pm, xx = lenght of data time = 03
    return time


def get_heat_level(data):
    sequence = data[12:]
    laseq = sequence[:8]
    #    print('sequence = '+laseq)
    dev = data[26:]
    deviceID = dev[:8]
    #    print('device ID = '+deviceID)
    tc1 = data[46:]
    tc2 = tc1[:2]
    return int(float.fromhex(tc2))


def set_temperature(
    temp_celcius,
):  # temperature is always in celcius sent as 0.01oC unit. 21.5oC sent as 2150
    temp = int(temp_celcius * 100)
    return "02" + bytearray(struct.pack("<i", temp)[:2]).hex()


def get_temperature(data):
    sequence = data[12:]
    laseq = sequence[:8]
    #    print('sequence = '+laseq)
    dev = data[26:]
    deviceID = dev[:8]
    #    print('device ID = '+deviceID)
    result = data[20:]
    status = result[:2]
    if status == "fc":
        return None  # device didn't answer, wrong device
    else:
        tc1 = data[46:]
        tc2 = tc1[:2]
        tc3 = data[48:]
        tc4 = tc3[:2]
        latemp = tc4 + tc2
        return float.fromhex(latemp) * 0.01


def to_celcius(temp):
    return round((temp - 32) * 0.5555, 2)


def from_celcius(temp):
    return round((temp + 1.8) + 32, 2)


def get_outside_temperature():  # https://api.darksky.net/forecast/{your dark sky key}/{latitude},{logitude}
    r = requests.get(
        "https://api.darksky.net/forecast/{Dark sky key}/{latitude},{longitude}?exclude=minutely,hourly,daily,alerts,flags"
    )
    ledata = r.json()
    return to_celcius(float(json.dumps(ledata["currently"]["temperature"])))


def set_is_away(away):  # 0=home,2=away
    return "01" + bytearray(struct.pack("<i", away)[:1]).hex()


def get_is_away(data):
    sequence = data[12:]
    laseq = sequence[:8]
    #    print('sequence = '+laseq)
    dev = data[26:]
    deviceID = dev[:8]
    #    print('device ID = '+deviceID)
    tc1 = data[46:]
    tc2 = tc1[:2]
    return int(float.fromhex(tc2))


def set_mode(mode):  # 0=off,1=freeze,2=manual,3=auto,5=away
    return "01" + bytearray(struct.pack("<i", mode)[:1]).hex()


def get_mode(data):
    sequence = data[12:]
    laseq = sequence[:8]
    #    print('sequence = '+laseq)
    dev = data[26:]
    deviceID = dev[:8]
    #    print('device ID = '+deviceID)
    tc1 = data[46:]
    tc2 = tc1[:2]
    return int(float.fromhex(tc2))


def set_intensity(num):
    return "01" + bytearray(struct.pack("<i", num)[:1]).hex()


def get_intensity(data):
    sequence = data[12:]
    laseq = sequence[:8]
    #    print('sequence = '+laseq)
    dev = data[26:]
    deviceID = dev[:8]
    #    print('device ID = '+deviceID)
    tc1 = data[46:]
    tc2 = tc1[:2]
    return int(float.fromhex(tc2))


def get_power_load(
    data,
):  # get power in watt, use by the device or connected to the device
    sequence = data[12:]
    laseq = sequence[:8]
    #    print('sequence = '+laseq)
    dev = data[26:]
    deviceID = dev[:8]
    #    print('device ID = '+deviceID)
    result = data[20:]
    status = result[:2]
    if status == "fc":
        return None  # device didn't answer, wrong device
    else:
        tc1 = data[46:]
        tc2 = tc1[:2]
        tc3 = data[48:]
        tc4 = tc3[:2]
        lepower = tc4 + tc2
        return int(float.fromhex(lepower))


def set_event_on(num):  # 1 = light on, 2 = light off, 3 = intensity changed
    b0 = "10"
    b1 = "00000000"
    b3 = "000000000000000000"
    if num == 1:
        b2 = "020000"  # event on = on
    elif num == 2:
        b2 = "000200"  # event off = on
    else:
        b2 = "000002"  # event dimmer = on
    return b0 + b1 + b2 + b3


def set_timer_on(num):  # 1 = light on, 2 = light off, 3 = intensity changed
    b0 = "10"
    b1 = "00000000"
    b3 = "000000000000000000"
    if num == 1:
        b2 = "010000"  # event on = timer start
    elif num == 2:
        b2 = "000100"  # event off = timer start
    else:
        b2 = "000001"  # event dimmer = timer start
    return b0 + b1 + b2 + b3


def set_event_off(num):  # 1 = light on, 2 = light off, 3 = intensity changed
    b0 = "10"
    b1 = "00000000"
    b3 = "000000000000000000"
    if num == 1:
        b2 = "000000"  # event = off
    elif num == 2:
        b2 = "000000"  # timer on
    else:
        b2 = "000000"  # event = on
    return b0 + b1 + b2 + b3


def get_event(data):
    sequence = data[12:]
    laseq = sequence[:8]
    #    print('sequence = '+laseq)
    dev = data[26:]
    deviceID = dev[:8]
    #    print('device ID = '+deviceID)
    tc1 = data[54:]
    tc2 = tc1[:6]
    return tc2  # int(float.fromhex(tc2))


def set_timer_length(num):  # 0=desabled, 1 to 255 lenght on
    return "01" + bytearray(struct.pack("<i", num)[:1]).hex()


def get_timer_length(data):  # 0=desabled, 1 to 255 lenght on
    sequence = data[12:]
    laseq = sequence[:8]
    #    print('sequence = '+laseq)
    dev = data[26:]
    deviceID = dev[:8]
    #    print('device ID = '+deviceID)
    tc1 = data[46:]
    tc2 = tc1[:2]
    return int(float.fromhex(tc2))


def get_result(data):  # check if data write was successfull, return True or False
    sequence = data[12:]
    laseq = sequence[:8]
    #    print('sequence = '+laseq)
    dev = data[26:]
    deviceID = dev[:8]
    #    print('device ID = '+deviceID)
    tc1 = data[20:]
    tc2 = tc1[:2]
    if str(tc2) == "0a":  # data read or write
        return True
    elif str(tc2) == "01":  # data report
        return True
    return False


def error_info(bug, device):
    if bug == b"FF":
        _LOGGER.debug("in request for %s : Request failed.", device)
    elif bug == b"FE":
        LOGGER.debug("in request for %s : Buffer full, retry later.", device)
    elif bug == b"FC":
        LOGGER.debug("in request for %s : Device not responding.", device)
    elif bug == b"FB":
        LOGGER.debug(
            "in request for %s : Abort failed, request not found in queue.", device
        )
    elif bug == b"FA":
        LOGGER.debug(
            "in request for %s : Unknown device or destination deviceID is invalid or not a member of this network.",
            device,
        )
    else:
        LOGGER.debug("in request for %s : Unknown error.", device)


def send_request(data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (SERVER, PORT)
    sock.connect(server_address)
    try:
        sock.sendall(login_request())
        if (
            binascii.hexlify(sock.recv(1024)) == b"55000c001101000000030000032000009c"
        ):  # login ok
            #         print('sending data request')
            sock.sendall(data)
            reply = sock.recv(1024)
            #         print('answer = "%s"' % binascii.hexlify(reply))
            if crc_check(
                reply
            ):  # receive acknoledge, check status and if we will receive more data
                seq_num = binascii.hexlify(reply)[
                    12:20
                ]  # sequence id to link response to the correct request
                deviceid = binascii.hexlify(reply)[26:33]
                status = binascii.hexlify(reply)[20:22]
                more = binascii.hexlify(reply)[
                    24:26
                ]  # check if we will receive other data
                if (
                    status == b"00"
                ):  # request status = ok for read and write, we go on (read=00, report=01, write=00)
                    if more == b"01":  # GT125 is sending another data
                        datarec = sock.recv(1024)
                        return datarec
                elif status == b"01":  # status ok for data report
                    return reply
                else:
                    error_info(status, deviceid)
                    return False
            return reply
    finally:
        sock.close()


def get_device_id():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (SERVER, PORT)
    sock.connect(server_address)
    try:
        sock.sendall(login_request())
        if (
            binascii.hexlify(sock.recv(1024)) == b"55000c001101000000030000032000009c"
        ):  # login ok
            #        print('Please push the two buttons on the device you want to identify')
            datarec = sock.recv(1024)
            id = bytearray(datarec).hex()[14:22]
        return id
    finally:
        sock.close()


def send_ping_request(data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (SERVER, PORT)
    sock.connect(server_address)
    try:
        sock.sendall(data)
        reply = sock.recv(1024)
        if crc_check(reply):
            return reply
    finally:
        sock.close()


def retreive_key(data):
    binary = data[18:]
    key = binary[:16]
    return key


def ping_request():
    ping_data = "550002001200"
    ping_crc = bytes.fromhex(crc_count(bytes.fromhex(ping_data)))
    return bytes.fromhex(ping_data) + ping_crc


def key_request(serial):
    key_data = "55000A000A01" + serial
    key_crc = bytes.fromhex(crc_count(bytes.fromhex(key_data)))
    return bytes.fromhex(key_data) + key_crc


def login_request():
    login_data = "550012001001" + Api_ID + Api_Key
    login_crc = bytes.fromhex(crc_count(bytes.fromhex(login_data)))
    return bytes.fromhex(login_data) + login_crc


def get_seq(seq):
    if seq == 0:
        seq = seq_num
    seq += 1
    return str(seq)


def count_data(data):
    size = int(len(data) / 2)
    return bytearray(struct.pack("<i", size)[:1]).hex()


def count_data_frame(data):
    size = int(len(data) / 2)
    return bytearray(struct.pack("<i", size)[:2]).hex()


def data_read_request(command, unit_id, data_app):  # 21310500 ou FFFFFFFF
    head = "5500"
    data_seq = get_seq(seq)
    data_type = "00"
    data_res = "000000000000"
    app_data_size = "04"
    size = count_data_frame(
        command + data_seq + data_type + data_res + unit_id + app_data_size + data_app
    )
    data_frame = (
        head
        + size
        + command
        + data_seq
        + data_type
        + data_res
        + unit_id
        + app_data_size
        + data_app
    )
    #    print('data frame = "%s"' % data_frame)
    read_crc = bytes.fromhex(crc_count(bytes.fromhex(data_frame)))
    return bytes.fromhex(data_frame) + read_crc


def data_report_request(
    command, unit_id, data_app, data
):  # data = size+time or size+temperature
    head = "5500"
    data_seq = get_seq(seq)
    data_type = "00"
    data_res = "000000000000"
    app_data_size = count_data(data_app + data)
    size = count_data_frame(
        command
        + data_seq
        + data_type
        + data_res
        + unit_id
        + app_data_size
        + data_app
        + data
    )
    data_frame = (
        head
        + size
        + command
        + data_seq
        + data_type
        + data_res
        + unit_id
        + app_data_size
        + data_app
        + data
    )
    #    print('data frame = "%s"' % data_frame)
    read_crc = bytes.fromhex(crc_count(bytes.fromhex(data_frame)))
    return bytes.fromhex(data_frame) + read_crc


def data_write_request(command, unit_id, data_app, data):  # data = size+data to send
    head = "5500"
    data_seq = get_seq(seq)
    data_type = "00"
    data_res = "000000000000"
    app_data_size = count_data(data_app + data)
    size = count_data_frame(
        command
        + data_seq
        + data_type
        + data_res
        + unit_id
        + app_data_size
        + data_app
        + data
    )
    data_frame = (
        head
        + size
        + command
        + data_seq
        + data_type
        + data_res
        + unit_id
        + app_data_size
        + data_app
        + data
    )
    #    print('data frame = "%s"' % data_frame)
    read_crc = bytes.fromhex(crc_count(bytes.fromhex(data_frame)))
    return bytes.fromhex(data_frame) + read_crc


# send ping to gt125
# if binascii.hexlify(send_ping_request(ping_request())) == b'55000200130021':
#    if Api_Key == None:
#      print("ok we can send the api_key request\n")
#      print("push the GT125 web button")
#      print('Api key : ',retreive_key(binascii.hexlify(send_request(key_request(Api_ID)))))
#      print('Copy this value in the Api_Key, replacing the _None_ value')

# print('Sending app data request')
### example data read request uncoment the one you want to test
# read thermostat heat level
# print(get_heat_level(bytearray(send_request(data_read_request(data_read_command,device_id,data_heat_level))).hex()))
# read room temperature or setpoint
# print(get_temperature(bytearray(send_request(data_read_request(data_read_command,device_id,data_temperature))).hex()))
# print(get_temperature(bytearray(send_request(data_read_request(data_read_command,device_id,data_setpoint))).hex()))
# get mode
# print(get_mode(bytearray(send_request(data_read_request(data_read_command,device_id,data_mode))).hex()))
# get light intensity
# print(get_intensity(bytearray(send_request(data_read_request(data_read_command,device_id,data_light_intensity))).hex()))
# get away mode (home or away)
# print(get_is_away(bytearray(send_request(data_read_request(data_read_command,device_id,data_away))).hex()))
# get timer event status from light
# print(get_timer_lenght(bytearray(send_request(data_read_request(data_read_command,device_id,data_light_timer))).hex()))

### data report request
# broadcast local time
# print(get_result(bytearray(send_request(data_report_request(data_report_command,device_id,data_time,set_time()))).hex()))

### data write request
### send outside temperature
# print(get_result(bytearray(send_request(data_write_request(data_write_command,device_id,data_setpoint,set_temperature(21.50)))).hex()))
### turn off light
# print(get_result(bytearray(send_request(data_write_request(data_write_command,device_id,data_light_intensity,set_intensity(100)))).hex()))
### example data write request
# print(binascii.hexlify(send_request(data_write_request(data_write_command,device_id,data_light_timer,set_timer_lenght(20)))))
# set thermostat to manual mode
# print(get_result(bytearray(send_request(data_write_request(data_write_command,device_id,data_mode,set_mode(2)))).hex()))
# set thermostat to home
# print(get_result(bytearray(send_request(data_write_request(data_write_command,device_id,data_away,set_is_away(0)))).hex()))
