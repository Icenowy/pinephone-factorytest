PinePhone factorytest software
==============================

Current tests

* MPU-6050, kernel interface check, built-in self-test run
* LIS3MDL, kernel interface check, built-in self-test run
* STK3335, kernel interface check
* RTL8723CS, wifi scan check
* EG25-G, check booting and sim connectivity
* OV5640, takes test picture
* GC2145, takes test picture
* touchscreen test
* Earpiece test
* Speaker test
* Headphone test
* Modem status page
* Incoming call status
* RGB notification led test
* Vibration motor test
* Flashlight and torch test
* ANX7688, flash firmware and verify it loads with a cable plugged in

After the tests are successfull a bundled OS image can be flashed, it supports compressed images and bmap files.