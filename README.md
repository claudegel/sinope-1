Update:

To support [HACS](https://community.home-assistant.io/t/custom-component-hacs/121727), this repository has been broken up into two.
- sinope-gt125 for devices management via direct conection to the gt125 web gateway
- sinope-1 for devices management via [Neviweb](http://neviweb.com) portal.

# Home Assistant Neviweb Custom Components

Here is a custom components to suport [Neviweb](https://neviweb.com/) in [Home Assistant](http://www.home-assistant.io). 
Neviweb is a platform created by Sinopé Technologies to interact with their smart devices like thermostats, light switches/dimmers and load controllers. It also supports some devices made by [Ouellet](http://www.ouellet.com/en-ca/products/thermostats-and-controls/neviweb%C2%AE-wireless-communication-controls.aspx). 

This custom component originally was able to load devices from one GT125 network connected to Neviweb. It as been updated to be able to load devices from two GT125 network connected to Neviweb. This will give you possibility to load devices from house and office or house and summer house at once. The two gateway should be GT125. Cannot be mixed with GT130. Use Neviweb130 custom component for this one. 

## Supported Devices
Here is a list of currently supported devices. Basically, it's everything that can be added in Neviweb.
- Thermostats
  - Sinopé TH1120RF-3000 Line voltage thermostat
  - Sinopé TH1120RF-4000 Line voltage thermostat
  - Sinopé TH1121RF-3000 Thermostat for public areas
  - Sinopé TH1121RF-4000 Thermostat for public areas
  - Sinopé TH1300RF Floor heating thermostat
  - Sinopé TH1400RF Low voltage thermostat
  - Sinopé TH1500RF Double-pole thermostat
  - *Ouellet OTH2750-GT Line voltage thermostat
  - *Ouellet OTH3600-GA-GT Floor heating thermostat
  - *Ouellet OTH4000-GT thermostat
  - *Flextherm INSTINCT Connect thermostat
- Lighting
  - Sinopé SW2500RF Light switch
  - Sinopé DM2500RF Dimmer 
- Specialized Control
  - Sinopé RM3200RF Load controller 40A
  - Sinopé RM3250RF Load controller 50A

*Not tested, but should be working well. Your feedback is appreciated if a device doesn't work.

## Prerequisite
You need to connect your devices to a GT125 web gateway and add them in your Neviweb portal before being able to interact with them within Home Assistant. Please refer to the instructions manual of your device or visit [Neviweb support](https://www.sinopetech.com/blog/support-cat/plateforme-nevi-web/).

There are three custom components giving you the choice to manage your devices via the neviweb portal or directly via your GT125 gateway:
- [Neviweb](https://github.com/claudegel/sinope-1) custom component to manage your devices via Neviweb portal.
- [Sinope](https://github.com/claudegel/sinope-gt125) custom component to manage your devices directly via your GT125 web gateway.
- [Neviweb130](https://github.com/claudegel/sinope-130) custom component to manage your devices connected to your GT130 gateway via Neviweb portal.

You need to install only one of them but both can be used at the same time on HA.

## Neviweb custom component to manage your device via Neviweb portal:
## Installation
There are two methods to install this custom component:
- via HACS component:
  - This repository is compatible with the Home Assistant Community Store ([HACS](https://community.home-assistant.io/t/custom-component-hacs/121727)).
  - After installing HACS, install 'sinope-1' from the store, and use the configuration.yaml example below.
- Manually via direct download:
  - Download the zip file of this repository using the top right, green download button.
  - Extract the zip file on your computer, then copy the entire `custom_components` folder inside your Home Assistant `config` directory (where you can find your `configuration.yaml` file).
  - Your config directory should look like this:

    ```
    config/
      configuration.yaml
      custom_components/
        neviweb/
          __init__.py
          light.py
          switch.py
          climate.py
          const.py
      ...
    ```

## Configuration

To enable Neviweb management in your installation, add the following to your `configuration.yaml` file, then restart Home Assistant.

```yaml
# Example configuration.yaml entry
neviweb:
  username: '<your Neviweb username>'
  password: '<your Neviweb password>'
  network: '<your first location in Neviweb>' (1er emplacement)
  network2: '<your second location in Neviweb>' (2e emplacement)
```

**Configuration options:**  

| key | required | default | description
| --- | --- | --- | ---
| **username** | yes |  | Your email address used to log in Neviweb.
| **password** | yes |  | Your Neviweb password.
| **network** | no | 1st location found | The name of the GT125 location you want to control.
| **network2** | no | 2nd location found | The name of the second GT125 location you want to control.
| **scan_interval** | no | 540 | The number of seconds between access to Neviweb to update device state. Sinopé asked for a minimum of 5 minutes between polling now so you can reduce scan_interval to 300. Don't go over 600, the session will expire.

If you have also a GT130 also connected to Neviweb the network parameter is mandatory or it is possible that during the setup, the GT130 network will be picked up accidentally. If you have only two GT125 network, you can omit there names as during setup, the first two network found will be picked up automatically. If you prefer to add networs names make sure that they are written «exactly» as in Neviweb. (first letter capitalized or not).

## Custom services
Automations require services to be able to send commande. Ex. light.turn_on. For the Neviweb devices connected to the GT125 it is possible to use custom services to send specific information to devices or to change some devices parameters. Those custom services can be accessed via development tool/services or can be used in automation:

- neviweb.set_second_display, allow to change setting of the thermostats second display from setpoint temperature to outdoor temperature. This need to be sent only once to each devices.
- neviweb.set_climate_keypad_lock, allow to lock the keypad of the climate device.
- neviweb.set_light_keypab_lock, allow to lock the keypad of the light device.
- neviweb.set_switch_keypab_lock, allow to lock the keypad of the switch device.
- neviweb.set_light_timer, allow to set a delay after which the light will close automatically.
- neviweb.set_switch_timer, allow to set a delay after which the switch will close automatically.
- neviweb.set_led_indicator, this allow to change led indicator color and intensity on light devices for «on» and «off» state. you can send any color in the RGB list via the three color parameters red, green and blue and you can set intensity of the led indicator.
- neviweb.set_time_format, to display time in 12h or 24h on thermostats.
- neviweb.set_temperature_format, to disply temperature in celsius or fahrenheit format on thermostats.
- neviweb.set_early_start, to set thermostat early start heating.
- neviweb.set_backlight, to set bakclight intensity in state «on» or «off» for thermostats.
- neviweb.set_wattage, to set wattageOverload for light devices.
- neviweb.set_setpoint_min, to set minimum setpoint temperature for thermostats.
- neviweb.set_setpoint_max, to set maximum setpoint temperature for thermostats.
- neviweb.set_light_away_mode, to set mode for light when occupency is set to away.
- neviweb.set_switch_away_mode, to set mode for switch when occupency is set to away.

## Catch Éco Sinopé signal for peak period

If you have at least on thermostat or one load controler registered with Éco Sinopé program, it is now possible to catch when Neviweb send the signal for pre-heating start period for thermostats or start signal for the load controler.
Three attributes have been added to know that peak period is comming:
- For thermostats:
eco_status: set to 0 during normal period, to 1, during pre-heat and peak period.
eco_power: set to 0 during normal operation, to 1 during pre-heat operation before peak period and 2 during low temperature setpoint during peak period
eco_optout: set to 0 normal operation during peak period, to 1 if somebody have changed the setpoint on the thermostat during peak period.
- For load controler:
eco_status: set to «none» during normal operation, to «Planned» 10 minutes before peak period and to «active» during peak period.

It is then possible to make an automation to set all devices ready for peak period.

## Troubleshooting
If you get a stack trace related to a Neviweb component in your `home-assistant.log` file, you can fill an issue in this repository.

You can also post in one of those threads to get help:
- https://community.home-assistant.io/t/sinope-line-voltage-thermostats/17157
- https://community.home-assistant.io/t/adding-support-for-sinope-light-switch-and-dimmer/38835

### Turning on Neviweb debug messages in `home-assistant.log` file

To have a maximum of information to help you, please provide a snippet of your `home-assistant.log` file. I've added some debug log messages that could help diagnose the problem.

Add thoses lines to your `configuration.yaml` file
   ```yaml
   logger:
     default: warning
     logs:
       custom_components.neviweb: debug
   ```
This will set default log level to warning for all your components, except for Neviweb which will display more detailed messages.

## Customization
Install Custom UI and add the following in your code:

Icons for heat level: create folder www in the root folder .homeassistant/www
copy the six icons there. You can find them under local/www
feel free to improve my icons and let me know. (See icon_view2.png)

For each thermostat add this code in `customize.yaml`
```yaml
climate.neviweb_climate_thermostat_name:
  templates:
    entity_picture: >
      if (attributes.heat_level < 1) return '/local/heat-0.png';
      if (attributes.heat_level < 21) return '/local/heat-1.png';
      if (attributes.heat_level < 41) return '/local/heat-2.png';
      if (attributes.heat_level < 61) return '/local/heat-3.png';
      if (attributes.heat_level < 81) return '/local/heat-4.png';
      return '/local/heat-5.png';
 ```  
 In `configuration.yaml` add this
```yaml
customize: !include customize.yaml
``` 

## Current Limitations
- Home Assistant doesn't support operation mode selection for light and switch entities. So you won't see any dropdown list in the UI where you can switch between Auto and Manual mode. You can only see the current mode in the attributes. TODO: register a new service to change operation_mode and another one to set away mode.

- If you're looking for the away mode in the Lovelace 'thermostat' card, you need to click on the three dots button on the top right corner of the card. That will pop a window were you'll find the away mode switch at the bottom.

## TO DO
- Document each available services for every platforms + available attributes.
- Explore how to automatically setup sensors in HA that will report the states of a specific device attribute (i.e. the wattage of a switch device)

## Contributing
You see something wrong or something that could be improved? Don't hesitate to fork me and send me pull requests.
