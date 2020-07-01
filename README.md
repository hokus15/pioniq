# pioniq
Extract the Hyundai Ioniq Electric battery data from OBDII and position and publishes it to MQTT broker

## Disclaimer
This is my first python programming experience and I'm not a Linux expert so I'm pretty sure that the scripts may be far from efficient so don't be too hard with me when you find that I'm not following best practices neither doing things in the most optimal way. If you find that the scripts may be improved (I'm sure they are), just raise a PR with your improvements. Thanks!!

## Needed Hardware
- [Raspberry Pi Zero W](https://www.amazon.es/Raspberry-Pi-Zero-wh/dp/B07BHMRTTY/ref=sr_1_5?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=Raspberry+Pi+Zero+W&qid=1593189037&s=electronics&sr=1-5)
- [LTE Stick Huawei E3372](https://www.amazon.es/Huawei-USB-Stick-E3372-Inal%C3%A1mbrica/dp/B013UURTL4/ref=sr_1_2?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=LTE+Stick+Huawei+E3372&qid=1593188977&s=electronics&sr=1-2)
- [ELM327 Bluetooth scanner](https://www.amazon.es/Bluetooth-Scanner-Diagn%C3%B3stico-Wireless-Mercedes/dp/B079HS1LWB/ref=sr_1_15?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=ELM327&qid=1593189429&s=electronics&sr=1-15)
- [USB car charger](https://www.amazon.es/gp/product/B01HYZ8QPO/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1)
- [USB GPS receiver GlobalSat BU-353-S4](https://www.amazon.es/GlobalSat-BU-353-S4-Receptor-SiRF-Star/dp/B008200LHW/ref=sr_1_2?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&crid=2ENXQ7W8O8JQE)
- [USB cable extender](https://www.amazon.es/Cable-SODIAL-enchufe-extnsion-conector/dp/B01EIYCERU/ref=sr_1_25?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=alargador+USB&qid=1593189217&s=electronics&sr=1-25)
- [USB to Micro USB adapter](https://www.amazon.es/gp/product/B003YKX6WM/ref=ppx_yo_dt_b_asin_title_o02_s00?ie=UTF8&psc=1)
- [USB OTG cable](https://www.amazon.es/UGREEN-10396P-Hembra-Tel%C3%A9fono-Paquete/dp/B00N9S9Z0G/ref=sr_1_3?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=usb+female+to+micro+usb&qid=1593628139&s=computers&sr=1-3)
- [Raspberry Pi Zero case](https://www.amazon.es/Gaoominy-Caja-para-Raspberry-Zero/dp/B07QV5RXCN/ref=sr_1_10?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&crid=2PS8DPO5AEH1F&dchild=1&keywords=caja+raspberry+pi+zero&qid=1593189549&s=electronics&sprefix=caja+rasp%2Celectronics%2C181&sr=1-10)
- [Velcro stickers](https://www.amazon.es/gp/product/B00P94TB52/ref=ppx_yo_dt_b_asin_title_o05_s00?ie=UTF8&psc=1)

## Setup of Raspberry Pi Zero W
### Install the OS
If you are new to Raspberry Pi, you should get some information about it [here](https://www.raspberrypi.org/).

If you are already familiar with the Raspberry Pi, you can start.

I recommend to use the Raspberry Pi OS (previously called Raspbian).
Use [Raspberry Pi Imager](https://www.raspberrypi.org/downloads/) for an easy way to install Raspberry Pi OS and other operating systems to an SD card ready to use with your Raspberry Pi.
Once you have Raspberry Pi Imager installed open it and:
* Under `Choose OS` option select `Raspberry Pi OS (other)` and then choose `Raspberry Pi OS Lite (32-bit)`
* Choose your SD card
* and Write it

### WLAN and SSH configuration
Before you can put the SD card into the Pi and boot it, you should enable SSH connections and configure the WLAN.

To enable ssh create an empty file called `ssh` in the root of your SD card

To configure WLAN create a file “wpa_supplicant.conf” with the following content and copy it in the root of your SD card.

*I recommend to configure your Home and Car WiFi in this step*

```
country=ES
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
network={
    ssid="<YOUR HOME WLAN SSID HERE>"
    psk="<YOUR HOME WLAN PASSWORD HERE>"
    priority=20
    key_mgmt=WPA-PSK
    id_str="home"
}

network={
    ssid="<YOUR CAR WLAN SSID HERE>"
    psk="<YOUR CAR WLAN PASSWORD HERE>"
    priority=1
    key_mgmt=WPA-PSK
    id_str="car"
}
```

### First Raspberry Pi startup
I recommend that you set up your home router to set a static address to the Raspberry Pi. As the procedure is different for every router, please google for some information on how to do it on your router.
Once you have set up your IP address, turn on your Raspberry Pi and use any SSH client to connect to it. The default username is `pi` the password `raspberry`

Change the default password by typing: `passwd`

Run raspi-config to Enable wait for network a boot (you may also want to change other settings such as Locale, Time Zone,...).

To do so type: `sudo raspi-config`

Scroll down to `3 Boot Options` and press enter.

Scroll down to `B2 Wait for Network at Boot` and press enter.

Select `YES`

This tells the Raspberry Pi to start wait for a network during the booting process

Save and exit the raspi-config file by selecting `OK` and then `Finish`. Then, reboot your Pi and your Pi should wait for a network before completely booting! BTW: Yes, this works with WiFi.

### Package intallation
First of all we need to get the latest updates from the OS (this may take a while, so relax and enjoy looking at the progress...)
```
sudo apt-get update
sudo apt-get upgrade
```

Reboot if needed.
```
sudo reboot
```

Then install needed packages for the scripts to run:
```
sudo apt-get install bluetooth bluez-tools blueman python python-pip git
pip install paho-mqtt obd
```

### Pairing OBD2 Bluetooth Dongle with Raspberry Pi
**IMPORTANT** ALL requirements need to be met to pair the OBD2 bluetooth with the Raspberry Pi:
1. OBD2 dongle is plugged into the OBD2 port of your IONIQ
2. Raspberry Pi is within the range of the OBD2 bluetooth dongle (<5m)
3. Raspberry Pi is connected to the Wi-Fi. I use a powerbank to give power the Raspberry Pi when its close to the car. In my case using the USB car charger makes to be out of WiFi range.
4. The vehicle is switched on

*I'm lucky and meeting all those requirements are easy for me!!!. If not you, will need to find an alternative way do it.*

Once those requirements are fulfilled you can start with the pairing process:
```
sudo bluetoothctl
```

Then when the `[bluetooth]#` promt is shown, type:
```
agent on
scan on
```

You will get a list of all Bluetooth devices in range. Here should also appear your OBD2 dongle. You will also see the device address (Format: XX: XX: XX: XX: XX: XX). Note down this address because it's important for the next steps!. Please in all the following commands replace `XX:XX:XX:XX:XX:XX` with the address of your OBD2 dongle.

Once identified your OBD2 device on the list type :
```
pair XX:XX:XX:XX:XX:XX
```

Now you have to enter the device code. Mostly it is “1234”or “0000”. If that worked, you still have to trust the device in general, so this procedure does not have to be repeated permanently:
```
trust XX:XX:XX:XX:XX:XX
```

To be able to access the OBD2 dongle, it must be integrated as a serial device. This needs to be done after each restart. To do this, we add the following line to the file `/etc/rc.local`
```
sudo rfcomm bind hci0 XX:XX:XX:XX:XX:XX 1
```

Then reboot the Raspberry Pi
```
sudo reboot
```

### Configuring the GPS
If you plan to use the GPS module please install as well needed packages:
```
sudo apt-get install gpsd gpsd-clients python-gps ntp
```

Now configure the gpsd daemon:
```
sudo nano /etc/default/gpsd
```

The file should look something like:
```
# Default settings for the gpsd init script and the hotplug wrapper.

# Start the gpsd daemon automatically at boot time
START_DAEMON="true"

# Use USB hotplugging to add new USB devices automatically to the daemon
USBAUTO="true"

# Devices gpsd should collect to at boot time.
# They need to be read/writeable, either by user gpsd or the group dialout.
DEVICES="/dev/ttyUSB0"

# Other options you want to pass to gpsd
GPSD_OPTIONS=""
```

And then restart the service.
```
sudo systemctl restart gpsd
```

For testing that GPS works, try to run `cgps` utility. Make sure you have the GPS USB plugged in in your Raspberry Pi port. You will need the USB to micro USB adapter.
```
cgps
```

You should see something like:
```
lqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqklqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqk
x    Time:       2020-07-01T17:03:30.000Z   xxPRN:   Elev:  Azim:  SNR:  Used: x
x    Latitude:    x.xxxxxxxxx N             xx   1    67    078    47      Y   x
x    Longitude:    y.yyyyyyyy E             xx   3    74    321    32      Y   x
x    Altitude:   124.967 m                  xx   4    37    183    19      Y   x
x    Speed:      0.00 kph                   xx   8    12    165    24      Y   x
x    Heading:    0.0 deg (true)             xx  11    43    138    44      Y   x
x    Climb:      0.00 m/min                 xx  14    24    045    40      Y   x
x    Status:     3D DIFF FIX (6 secs)       xx  17    34    309    26      Y   x
x    Longitude Err:   +/- 10 m              xx  19    15    319    27      Y   x
x    Latitude Err:    +/- 4 m               xx  22    66    034    39      Y   x
x    Altitude Err:    +/- 19 m              xx  28    13    264    22      Y   x
x    Course Err:      n/a                   xx  31    10    079    27      Y   x
x    Speed Err:       +/- 72 kph            xx 123    35    138    43      Y   x
x    Time offset:     1.264                 xx                                 x
x    Grid Square:     JM19ip                xx                                 x
mqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqjmqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqj
#precedence ::ffff:0:0/96  100

#
# scopev4  <mask>  <value>
#    Add another rule to the RFC 6724 scope table for IPv4 addresses.
#    By default the scope IDs described in section 3.2 in RFC 6724 are
#    used.  Changing these defaults should hardly ever be necessary.
#    The defaults are equivalent to:
#
#scopev4 ::ffff:169.254.0.0/112  2
#scopev4 ::ffff:127.0.0.0/104    2
#scopev4 ::ffff:0.0.0.0/96       14
Mobility Support for IPv6 [RFC3775]
udplite 136     UDPLite         # UDP-Lite [RFC3828]
mpls-in-ip 137  MPLS-in-IP      # MPLS-in-IP [RFC4023]
manet   138                     # MANET Protocols [RFC5498]
hip     139     HIP             # Host Identity Protocol
shim6   140     Shim6           # Shim6 Protocol [RFC5533]
wesp    141     WESP            # Wrapped Encapsulating Security Payload
rohc    142     ROHC            # Robust Header Compression

H.10- 04/25/2019 115","activated":"2020-07-01T17:03:24.423Z","flags":1,"native":1,"bps":4800,"parity":"N","stopbits":1,"cycle":1.00}]}
{"class":"WATCH","enable":true,"json":true,"nmea":false,"raw":0,"scaled":false,"timing":false,"split24":false,"pps":false}
{"class":"TPV","device":"/dev/ttyUSB0","status":2,"mode":3,"time":"2020-07-01T17:03:24.000Z","ept":0.005,"lat":x.xxxxxxxxxxx,"lon":y.yyyyyyyyyyyy,"alt":124.967,"epx":10.106,"epy":4.597,"epv":19.127,"track":0.0000,"speed":0.000,"climb":0.000,
"eps":20.21,"epc":38.25}
```

If you are not getting GPS coordinates something may be wrong.

### Installing Python Scripts

Now that we can stablish connection with OBD2 dongle and the GPS is working we can install the scripts that will do all the magic!

Maybe it's not the best practise but I install the scripts in the pi home directory `/home/pi`.

To do so clone the Github repo:
```
cd ~
git clone https://github.com/hokus15/pioniq.git
```

### Execute the Python Scripts

To test if everything works:
1. [ELM327 Bluetooth scanner](https://www.amazon.es/Bluetooth-Scanner-Diagn%C3%B3stico-Wireless-Mercedes/dp/B079HS1LWB/ref=sr_1_15?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=ELM327&qid=1593189429&s=electronics&sr=1-15) is plugged into the OBD2 port of your IONIQ
2. [USB car charger](https://www.amazon.es/gp/product/B01HYZ8QPO/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) is plugged into the 12V plug of your IONIQ.
3. [LTE Stick Huawei E3372](https://www.amazon.es/Huawei-USB-Stick-E3372-Inal%C3%A1mbrica/dp/B013UURTL4/ref=sr_1_2?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=LTE+Stick+Huawei+E3372&qid=1593188977&s=electronics&sr=1-2) is plugged into the USB car charger (you may want to use the [USB cable extender](https://www.amazon.es/Cable-SODIAL-enchufe-extnsion-conector/dp/B01EIYCERU/ref=sr_1_25?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=alargador+USB&qid=1593189217&s=electronics&sr=1-25) to hide a bit the stick).
3. Raspberry Pi is plugged into the USB car charger using the [USB to Micro USB adapter](https://www.amazon.es/gp/product/B003YKX6WM/ref=ppx_yo_dt_b_asin_title_o02_s00?ie=UTF8&psc=1)
4. [Optional] [USB GPS receiver GlobalSat BU-353-S4](https://www.amazon.es/GlobalSat-BU-353-S4-Receptor-SiRF-Star/dp/B008200LHW/ref=sr_1_2?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&crid=2ENXQ7W8O8JQE) is plugged to the Raspberry Pi using the [USB OTG cable](https://www.amazon.es/UGREEN-10396P-Hembra-Tel%C3%A9fono-Paquete/dp/B00N9S9Z0G/ref=sr_1_3?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=usb+female+to+micro+usb&qid=1593628139&s=computers&sr=1-3)
5. The vehicle is switched on
6. The Raspberry Pi has been connected to the car WiFi

Run the command:
```
python pioniq/battery_data.py
```

This should publish battery information to the configured MQTT server.

If this works congratulations you are almost done!

### Run autoamtically Battery data script

To run the `battery_data.py` script automatically every minute, we need to set up a cron job, to do so:
```
crontab -e
```

And configure the following cron job:
```
* * * * * python /home/pi/pioniq/battery_data.py& PID=$!; sleep 55; kill $PID >/dev/null 2>&1
```

### Run autoamtically GPS data script

**OPTIONAL** This only needs to be done if you have the GPS device and you want to publish your IONIQ location.

To run the `gps_data.py` script automatically we need to set it up as a service, to do so:

Create a file called `gps_data.service` in `/etc/systemd/system` folder with the follwing content:
```
[Unit]
Description=Publish GPS data to MQTT
After=network-online.target

[Service]
WorkingDirectory=/home/pi/
User=pi
Type=idle
ExecStart=/usr/bin/python /home/pi/pioniq/gps_data.py

[Install]
WantedBy=multi-user.target
```

Then we need to enable the service like this:
```
sudo systemctl daemon-reload
sudo systemctl enable gps_data.service
```

## Car WiFi
To have WiFi in the car, I use a UBS powered stick that as soon as it get some power it startup and connects to the 4G LTE network and operates as a WiFi router.
In my case I use the [Huawei E3372 LTE stick](https://www.amazon.es/Huawei-USB-Stick-E3372-Inal%C3%A1mbrica/dp/B013UURTL4/ref=sr_1_2?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=LTE+Stick+Huawei+E3372&qid=1593188977&s=electronics&sr=1-2). Please refer to your specific stick instructions on how to configure it.

## Loggly installation
**OPTIONAL**
As the Raspberry Pi will usually run in your car's WiFi there is going to be complex for you to debug or debug problems or even look at the log files. For that I'm using a Log Management tool in the cloud that offers a free tier more than enought for the purpose of this project (200 MB/day and 7 days log retention).

Just create a free account in [Loggly](https://www.loggly.com/) and follow instructions on how to [Linux Log File Monitoring](https://documentation.solarwinds.com/en/Success_Center/loggly/Content/admin/file-monitoring.htm).

## Credits
All this work has been possible by putting together different pieces like:
- How To Article from [sochack.eu](https://tutorial.sochack.eu/en/how-to-soc/)
- [Ingesting GPS Data From Raspberry PI Zero Wireless With a USB GPS Device](https://dzone.com/articles/iot-ingesting-gps-data-from-raspberry-pi-zero-wire)
- [python-OBD](https://github.com/brendan-w/python-OBD/tree/master/obd)
- [EVNotiPi](https://github.com/EVNotify/EVNotiPi)
- and of course lot of patience and [Google](https://www.google.com/)