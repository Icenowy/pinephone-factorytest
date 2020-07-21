import io
import math
import shutil
import subprocess
import threading
import time
from io import SEEK_END
import lzma

import gi
import logging
import glob
import os
import re

# For chip self-tests
import factorytest.selftest as selftest

# For modem tests
import factorytest.modem as modem

# For wifi tests
from wifi import Cell, Scheme

# For camera tests
import factorytest.camera as camera

# For audio tests
import factorytest.audio as audio

# For led tests
import factorytest.led as led
from factorytest import motor

# For anx7688 tests
import factorytest.anx as anx

from factorytest.bmap.bmapcopy import BmapCopy

try:
    import importlib.resources as pkg_resources
except ImportError:
    import importlib_resources as pkg_resources

import pkg_resources as pkgr

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GObject, Gio, GdkPixbuf

logging.basicConfig(level=logging.DEBUG)


def mess_with_permissions():
    subprocess.call(['sudo', 'chmod', '777', '/dev/i2c-1'])


def unload_driver(name):
    subprocess.call(['sudo', 'rmmod', name])


def load_driver(name):
    subprocess.call(['sudo', 'modprobe', name])


class AutoTests(threading.Thread):
    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.callback = callback

    def run(self):
        # i2c sensor tests
        GLib.idle_add(self.callback, ['Testing MPU-6050', 0, None])
        result = self.test_sensor('mpu6050', 'in_accel_x_raw')
        unload_driver('inv_mpu6050_i2c')
        result &= selftest.mpu6050(1, 0x68)
        load_driver('inv_mpu6050_i2c')
        GLib.idle_add(self.callback, ['Testing LIS3MDL', 1, ('sixaxis', result)])
        result = self.test_sensor('lis3mdl', 'in_magn_x_raw')
        unload_driver('st_magn_i2c')
        result &= selftest.lis3mdl(1, 0x1e)
        load_driver('st_magn_i2c')
        GLib.idle_add(self.callback, ['Testing STK3335', 2, ('magnetometer', result)])
        result = self.test_sensor('stk3310', 'in_proximity_raw')
        GLib.idle_add(self.callback, ['Testing RTL8723CS', 3, ('proximity', result)])

        # wifi test
        result = False
        for _ in range(0, 10):
            try:
                if len(list(Cell.all('wlan0'))) > 0:
                    result = True
                    break
            except:
                time.sleep(1)

        GLib.idle_add(self.callback, ['Testing EG25', 4, ('wifi', result)])

        # modem test
        result = modem.test_eg25()
        GLib.idle_add(self.callback, ['Testing ANX7688', 5, ('modem', result)])

        # anx7688 test
        result = anx.test_anx()
        GLib.idle_add(self.callback, ['Testing OV5640', 6, ('anx', result)])


        # Rear camera
        result = camera.check_ov5640()
        GLib.idle_add(self.callback, ['Testing GC2145', 7, ('rearcam', result)])

        # Front camera
        result = camera.check_gc2145()
        GLib.idle_add(self.callback, ['Done', 8, ('frontcam', result)])

    def test_sensor(self, name, attribute):
        for device in glob.glob('/sys/bus/iio/devices/iio:device*'):

            if os.path.isfile(os.path.join(device, 'name')):
                with open(os.path.join(device, 'name')) as handle:
                    if handle.read().strip() != name:
                        continue

                try:
                    with open(os.path.join(device, attribute)) as handle:
                        handle.read()
                        return True
                except:
                    return False

        return False


class ModemInfo:
    def __init__(self):
        self.status = None
        self.registration = None
        self.imei = None
        self.signal = None
        self.network = None
        self.firmware = None
        self.sim_status = None
        self.imsi = None
        self.call_status = None
        self.call_technology = None
        self.call_number = None


class ModemTests(threading.Thread):
    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.callback = callback
        self.running = True

    def run(self):
        print("Started modem test")
        result = ModemInfo()
        result.status = "Waiting for modem"
        GLib.idle_add(self.callback, result)
        if not modem.check_usb_exists('2c7c', '0125'):
            GLib.idle_add(self.callback, result)
            if modem.try_poweron():
                result.status = "Idle"
            else:
                result.status = "Boot timeout"
            GLib.idle_add(self.callback, result)

        modem.fix_tty_permissions()

        result.status = "Connected to modem, loading info"
        time.sleep(3)
        _, result.imei = modem.get_imei()
        GLib.idle_add(self.callback, result)
        _, result.firmware = modem.get_firmware()
        GLib.idle_add(self.callback, result)
        result.network = modem.get_network()
        GLib.idle_add(self.callback, result)
        signal = modem.get_signal()
        result.registration = modem.get_operator()
        if signal is not None:
            if signal[1] < 99:
                result.signal = "{} ({} Rxqual)".format(signal[0], signal[1])
            else:
                result.signal = signal[0]
        GLib.idle_add(self.callback, result)
        status, imsi = modem.get_imsi()
        if status == "OK":
            result.imsi = imsi
            result.sim_status = "Connected"
        else:
            result.sim_status = "No sim"
        result.status = "OK"
        GLib.idle_add(self.callback, result)

        modem.set_auto_answer()
        result.call_status = 'Ready for call'
        had_call = False
        while self.running:
            call = modem.get_call_info()
            result.network = modem.get_network()
            signal = modem.get_signal()
            result.registration = modem.get_operator()
            if signal is not None:
                if signal[1] < 99:
                    result.signal = "{} ({} Rxqual)".format(signal[0], signal[1])
                else:
                    result.signal = signal[0]

            if call is not None:
                result.call_status = "{} ({})".format(call['direction'], call['state'])
                result.call_technology = call['mode']
                result.call_number = call['number']
                GLib.idle_add(self.callback, result)
                if not had_call:
                    had_call = True
                    modem.do_dtmf(result.call_number.replace("+", ""))
            else:
                result.call_status = 'Ready for call'
                result.call_technology = None
                result.call_number = None
                GLib.idle_add(self.callback, result)
            time.sleep(1)


class Flasher(threading.Thread):
    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.callback = callback

    def run(self):
        print("Started flashing procedure")
        GLib.idle_add(self.callback, ['Starting flashing procedure', 0.0])
        subprocess.run(['sudo', 'chmod', '777', '/dev/mmcblk2'])

        with open('/usr/share/factorytest/label.txt') as handle:
            label = handle.read()

        GLib.idle_add(self.callback, ['Flashing {}'.format(label), 0.0])

        if os.path.isfile('/usr/share/factorytest/os.img.bmap'):
            self.run_bmap(label)
        else:
            self.run_dd(label)

        GLib.idle_add(self.callback, ['Purging caches...', 1.0])
        subprocess.run(['sudo', 'sync'])
        GLib.idle_add(self.callback, ['Flashing complete!', 1.0])

    def run_dd(self, label):
        done = 0
        blocksize = 1024 * 1024 * 5

        with open('/usr/share/factorytest/filesize.txt') as handle:
            size = int(handle.read().strip())

        blocks = size / blocksize
        with lzma.open('/usr/share/factorytest/os.img.xz', 'rb') as sd:
            with open('/dev/mmcblk2', 'wb') as emmc:
                while True:
                    block = sd.read(blocksize)
                    if block is None or len(block) == 0:
                        break
                    emmc.write(block)
                    done += 1
                    GLib.idle_add(self.callback, ['Writing {}'.format(label), done / blocks])

    def run_bmap(self, label):
        with lzma.open('/usr/share/factorytest/os.img.xz', 'rb') as image:
            image.name = '/usr/share/factorytest/os.img.xz'
            with open('/dev/mmcblk2', 'wb') as emmc:
                with open('/usr/share/factorytest/os.img.bmap', 'rb') as bmap:
                    instance = BmapCopy(image, emmc, bmap)
                    instance.on_progress = lambda percent: GLib.idle_add(self.callback,
                                                                         ['Writing {}'.format(label), percent / 100.0])
                    instance.copy()


class FactoryTestApplication(Gtk.Application):
    def __init__(self, application_id, flags):
        Gtk.Application.__init__(self, application_id=application_id, flags=flags)
        self.connect("activate", self.new_window)

    def new_window(self, *args):
        AppWindow(self)


class AppWindow:
    def __init__(self, application):
        self.application = application
        builder = Gtk.Builder()
        with pkg_resources.path('factorytest', 'factorytest.glade') as ui_file:
            builder.add_from_file(str(ui_file))
        builder.connect_signals(Handler(builder))

        window = builder.get_object("main_window")
        window.set_application(self.application)
        window.show_all()

        Gtk.main()


class Handler:
    def __init__(self, builder):
        self.builder = builder
        self.window = builder.get_object('main_window')
        self.stack = builder.get_object('main_stack')

        # Menu buttons
        self.test_auto = builder.get_object('test_auto')
        self.test_touchscreen = builder.get_object('test_touchscreen')
        self.test_earpiece = builder.get_object('test_earpiece')
        self.test_modem = builder.get_object('test_modem')
        self.test_flash = builder.get_object('test_flash')
        self.test_torch = builder.get_object('test_torch')
        self.test_headphone = builder.get_object('test_headphone')
        self.test_speaker = builder.get_object('test_speaker')
        self.test_rgb = builder.get_object('test_rgb')
        self.test_motor = builder.get_object('test_motor')
        self.flash_emmc = builder.get_object('flash_emmc')

        # Stack pages
        self.page_main = builder.get_object('page_main')
        self.page_progress = builder.get_object('page_progress')
        self.page_touchscreen = builder.get_object('page_touchscreen')
        self.page_yesno = builder.get_object('page_yesno')
        self.page_modem = builder.get_object('page_modem')
        self.page_flasher = builder.get_object('page_flasher')

        # Progress page
        self.progress_status = builder.get_object('progress_status')
        self.progress_bar = builder.get_object('progress_bar')
        self.progress_log = builder.get_object('progress_log')
        self.img_front = builder.get_object('img_front')
        self.img_rear = builder.get_object('img_rear')

        # Touchscreen page
        self.touchscreen_horisontal = builder.get_object('touchscreen_horisontal')
        self.touchscreen_vertical = builder.get_object('touchscreen_vertical')

        # Yes/no page
        self.yesno_label = builder.get_object('yesno_label')
        self.yesno_yes = builder.get_object('yesno_yes')
        self.yesno_no = builder.get_object('yesno_no')

        # Modem page
        self.modem_status = builder.get_object('modem_status')
        self.modem_registration = builder.get_object('modem_registration')
        self.modem_imei = builder.get_object('modem_imei')
        self.modem_firmware = builder.get_object('modem_firmware')
        self.modem_network = builder.get_object('modem_network')
        self.modem_signal = builder.get_object('modem_signal')
        self.modem_sim_status = builder.get_object('modem_sim_status')
        self.modem_sim_imsi = builder.get_object('modem_sim_imsi')
        self.modem_call_status = builder.get_object('modem_call_status')
        self.modem_call_technology = builder.get_object('modem_call_technology')
        self.modem_call_number = builder.get_object('modem_call_number')

        # Flasher page
        self.flasher_status = builder.get_object('flasher_status')
        self.flasher_progress = builder.get_object('flasher_progress')
        self.flasher_button = builder.get_object('flasher_button')

        # Result storage
        self.auto_result = []
        self.tstest_clicked = set()
        self.yesno_button = None
        self.modem_hide_ids = False
        self.modem_last = None

        version = pkgr.get_distribution('factorytest_pinephone').version
        self.window.set_title("factorytest v{}".format(version))

        mess_with_permissions()

        if os.path.isfile("/usr/share/factorytest/label.txt"):
            with open('/usr/share/factorytest/label.txt') as handle:
                label = handle.read()
            self.flasher_button.get_children()[0].set_label("Overwrite eMMC with {}".format(label))
        else:
            self.flasher_button.set_sensitive(False)

    def on_quit(self, *args):
        Gtk.main_quit()

    def on_test_auto_clicked(self, *args):
        self.stack.set_visible_child(self.page_progress)
        self.auto_result = []
        thread = AutoTests(self.autotests_update)
        thread.start()

    def on_test_modem_clicked(self, *args):
        self.stack.set_visible_child(self.page_modem)
        thread = ModemTests(self.modemtests_update)
        thread.start()

    def on_flash_emmc_clicked(self, button):
        self.stack.set_visible_child(self.page_flasher)

    def on_back_clicked(self, *args):
        self.stack.set_visible_child(self.page_main)

    def autotests_update(self, result):
        self.progress_status.set_text(result[0])
        fraction = result[1] / 8.0
        self.progress_bar.set_fraction(fraction)

        update = result[2]
        if update is not None:
            ob = self.builder.get_object('result_' + update[0])
            if update[1] is True:
                ob.set_text('OK')

                if update[0] == 'rearcam':
                    self.img_rear.set_from_file('/tmp/ov5640.png')
                elif update[0] == 'frontcam':
                    self.img_front.set_from_file('/tmp/gc2145.png')

            elif update[1] is False:
                self.auto_result.append(update[1])
                ob.set_text('failed')
            else:
                if update[1] != "Skipped":
                    self.auto_result.append(update[1])
                ob.set_text(update[1])

        if result[0] == "Done":
            if len(self.auto_result) > 0:
                self.test_auto.get_style_context().add_class('destructive-action')
                self.test_auto.get_style_context().remove_class('suggested-action')
            else:
                self.test_auto.get_style_context().add_class('suggested-action')
                self.test_auto.get_style_context().remove_class('destructive-action')
            self.on_test_update()

        self.page_progress.show_all()

    def modemtests_update(self, result):
        """
        :type result: ModemInfo
        """
        print("Got modem update!")
        self.modem_status.set_text(result.status if result.status is not None else "...")
        self.modem_registration.set_text(result.registration if result.registration is not None else "...")
        if self.modem_hide_ids is True:
            self.modem_imei.set_text("[Hidden]")
        else:
            self.modem_imei.set_text(result.imei if result.imei is not None else "...")
        self.modem_firmware.set_text(result.firmware if result.firmware is not None else "...")
        self.modem_network.set_text(result.network if result.network is not None else "...")
        self.modem_signal.set_text(result.signal if result.signal is not None else "...")

        self.modem_sim_status.set_text(result.sim_status if result.sim_status is not None else "...")
        if self.modem_hide_ids is True:
            self.modem_sim_imsi.set_text("[Hidden]")
        else:
            self.modem_sim_imsi.set_text(result.imsi if result.imsi is not None else "...")

        self.modem_call_status.set_text(result.call_status if result.call_status is not None else "...")
        self.modem_call_technology.set_text(result.call_technology if result.call_technology is not None else "...")
        if self.modem_hide_ids is True:
            self.modem_call_number.set_text("[Hidden]")
        else:
            self.modem_call_number.set_text(result.call_number if result.call_number is not None else "...")

        self.page_modem.show_all()
        self.modem_last = result

    def on_modem_hide_ids_toggled(self, button):
        self.modem_hide_ids = button.get_active()
        self.modemtests_update(self.modem_last)

    def on_test_touchscreen_clicked(self, *args):
        self.stack.set_visible_child(self.page_touchscreen)

    def on_tstest_click(self, button):
        self.tstest_clicked.add(button)
        button.get_style_context().add_class('suggested-action')
        if len(self.tstest_clicked) == 12:
            self.test_touchscreen.get_style_context().add_class('suggested-action')
            self.on_test_update()

    def run_yesno(self, button, question):
        self.yesno_button = button
        self.yesno_label.set_text(question)
        self.page_yesno.show_all()
        self.stack.set_visible_child(self.page_yesno)

    def on_yesno_yes_clicked(self, *args):
        button = self.builder.get_object('test_{}'.format(self.yesno_button))
        button.get_style_context().add_class('suggested-action')
        button.get_style_context().remove_class('destructive-action')
        self.page_main.show_all()
        self.stack.set_visible_child(self.page_main)
        self.on_test_update()

    def on_yesno_no_clicked(self, *args):
        button = self.builder.get_object('test_{}'.format(self.yesno_button))
        button.get_style_context().add_class('destructive-action')
        button.get_style_context().remove_class('suggested-action')
        self.page_main.show_all()
        self.stack.set_visible_child(self.page_main)
        self.on_test_update()

    def on_test_earpiece_clicked(self, *args):
        self.run_yesno('earpiece', 'Does sound come out of the earpiece?')
        audio.test_earpiece()
        audio.test_earpiece()

    def on_test_headphone_clicked(self, *args):
        self.run_yesno('headphone', 'Does sound come out of the headphones?')
        audio.test_headphones()
        audio.test_headphones()

    def on_test_speaker_clicked(self, *args):
        self.run_yesno('speaker', 'Does sound come out of the speaker?')
        audio.test_speaker()
        audio.test_speaker()

    def on_test_rgb_clicked(self, *args):
        self.run_yesno('rgb', 'Does the notification led light red,green,blue,white?')
        led.fix_led_permissions()
        led.test_notification_led()

    def on_test_motor_clicked(self, *args):
        self.run_yesno('motor', 'Does vibration motor work?')
        motor.test_motor()

    def on_test_flash_clicked(self, *args):
        self.run_yesno('flash', 'Does the camera flash work?')
        led.test_flash()

    def on_test_torch_clicked(self, *args):
        self.run_yesno('torch', 'Does the flashlight light up?')
        led.test_torch()

    def on_flasher_button_clicked(self, button):
        button.set_sensitive(False)
        thread = Flasher(self.on_flasher_update)
        thread.start()

    def on_flasher_update(self, progress):
        status, progress = progress
        self.flasher_status.set_text(status)
        self.flasher_progress.set_fraction(progress)

    def on_test_update(self):
        passed = 0
        if self.test_auto.get_style_context().has_class('suggested-action'):
            passed += 1
        if self.test_earpiece.get_style_context().has_class('suggested-action'):
            passed += 1
        if self.test_headphone.get_style_context().has_class('suggested-action'):
            passed += 1
        if self.test_speaker.get_style_context().has_class('suggested-action'):
            passed += 1
        if self.test_flash.get_style_context().has_class('suggested-action'):
            passed += 1
        if self.test_torch.get_style_context().has_class('suggested-action'):
            passed += 1
        if self.test_rgb.get_style_context().has_class('suggested-action'):
            passed += 1
        if self.test_touchscreen.get_style_context().has_class('suggested-action'):
            passed += 1
        if self.test_motor.get_style_context().has_class('suggested-action'):
            passed += 1

        if passed == 9:
            self.flash_emmc.set_sensitive(True)


def main():
    print("Starting factorytest")
    app = FactoryTestApplication("org.pine64.pinephone.factorytest", Gio.ApplicationFlags.FLAGS_NONE)
    app.run()


if __name__ == '__main__':
    main()
