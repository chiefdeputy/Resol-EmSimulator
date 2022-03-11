# Resol-EmSimulator
Home Assistant Addon project to simulate an EM device for Resol V-Bus. This is a proof of concept and probably not working very well.

## Installation
This is WIP. So there's no convenient way to istall it yet. Get the terminal addon and checkout this repo to your ´´/addon´´ folder in home assistant. Add local addons in supervisor settings and build the container by installing it.

**On Arm devices this can take up to 15 minutes!**

## Configuration
Configuration values:
```
  host: "192.168.1.2"
  password: "vbus"
  sensors:
    - switch.to_publish_as_sensor1
    - light.to_publish_as_sensor2
    - input_boolean_to publish_as_sensor_3
    - input_number.to publish_as_sensor_4
    - sensor.to_publish_as_sensor_5
  json_server: falses
```
| Config        | Value    | Description |
|---------------|----------|-------------|
|``host``       | ip       | The ip address of the VBus/Lan, KM2 or DLx device to use. |
|``password``   | string   | The password of the VBus endpoint. Do not confuse this with the data endpoint of DLx/KM devices! |
|``sensors``    |\[string\]| A List of **up to five** enitity_ids from your local home assistant instance. |
|``json_server``| bool     | Enable the webserver to serve packages received yia vbus as json. |

## json webserver
In the future it is planned to use the custom component [hass-Deltasol-KM2](https://github.com/dm82m/hass-Deltasol-KM2) of @dm82m to provide entity_ids to home assistant using the json_server component of this addon.

## Credits
* VBus java library and em-simulation example by @danielwippermann: [resol-vbus-java](https://github.com/danielwippermann/resol-vbus-java)

## Legal Notices
RESOL, VBus, VBus.net and others are trademarks or registered trademarks
of RESOL - Elektronische Regelungen GmbH.

### Used VBus Java Library
Copyright (C) 2008-2016, RESOL - Elektronische Regelungen GmbH.

Copyright (C) 2016-2018, Daniel Wippermann.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so.
