import subprocess
import threading
import time

import gi
import logging
import glob
import os

# For chip self-tests
import factorytest.selftest as selftest

# For modem tests
import factorytest.modem as modem

# For wifi tests
from wifi import Cell, Scheme

# For camera tests
import factorytest.camera as camera

try:
    import importlib.resources as pkg_resources
except ImportError:
    import importlib_resources as pkg_resources

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
        GLib.idle_add(self.callback, ['Testing OV5640', 5, ('modem', result)])

        # Rear camera
        result = True
        GLib.idle_add(self.callback, ['Testing GC2145', 6, ('rearcam', result)])

        # Front camera
        result = True
        GLib.idle_add(self.callback, ['Done', 7, ('frontcam', result)])

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


class ModemTests(threading.Thread):
    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.callback = callback

    def run(self):
        result = ModemInfo()
        result.status = "Booting"
        if not modem.check_usb_exists('2c7c', '0125'):
            GLib.idle_add(self.callback, result)
            if modem.try_poweron():
                result.status = "Idle"
            else:
                result.status = "Boot timeout"
            GLib.idle_add(self.callback, result)

        modem.fix_tty_permissions()

        _, result.imei = modem.get_imei()
        _, result.firmware = modem.get_firmware()
        result.network = modem.get_network()
        signal = modem.get_signal()
        if signal is not None:
            result.signal = "{} ({} Rxqual)".format(signal[0], signal[1])

        status, imsi = modem.get_imsi()
        if status == "ok":
            result.imsi = imsi
            result.sim_status = "Connected"
        else:
            result.sim_status = "No sim"


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

        # Stack pages
        self.page_main = builder.get_object('page_main')
        self.page_progress = builder.get_object('page_progress')
        self.page_touchscreen = builder.get_object('page_touchscreen')
        self.page_yesno = builder.get_object('page_yesno')
        self.page_modem = builder.get_object('page_modem')

        # Progress page
        self.progress_status = builder.get_object('progress_status')
        self.progress_bar = builder.get_object('progress_bar')
        self.progress_log = builder.get_object('progress_log')

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

        # Result storage
        self.auto_result = []
        self.tstest_clicked = set()
        self.yesno_button = None

        mess_with_permissions()

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

    def on_back_clicked(self, *args):
        self.stack.set_visible_child(self.page_main)

    def autotests_update(self, result):
        self.progress_status.set_text(result[0])
        fraction = result[1] / 7.0
        self.progress_bar.set_fraction(fraction)

        update = result[2]
        if update is not None:
            self.auto_result.append(update[1])
            ob = self.builder.get_object('result_' + update[0])
            if update[1]:
                ob.set_text('OK')
            else:
                ob.set_text('failed')

        if result[0] == "Done":
            if False in self.auto_result:
                self.test_auto.get_style_context().add_class('destructive-action')
                self.test_auto.get_style_context().remove_class('suggested-action')
            else:
                self.test_auto.get_style_context().add_class('suggested-action')
                self.test_auto.get_style_context().remove_class('destructive-action')

        self.page_progress.show_all()

    def modemtests_update(self, result):
        """
        :type result: ModemInfo
        """
        self.modem_status.set_text(result.status if result.status is not None else "...")
        self.modem_registration.set_text(result.registration if result.registration is not None else "...")
        self.modem_imei.set_text(result.imei if result.imei is not None else "...")
        self.modem_firmware.set_text(result.firmware if result.firmware is not None else "...")
        self.modem_network.set_text(result.network if result.network is not None else "...")
        self.modem_signal.set_text(result.signal if result.signal is not None else "...")
        self.modem_sim_status.set_text(result.sim_status if result.sim_status is not None else "...")
        self.modem_sim_imsi.set_text(result.imsi if result.imsi is not None else "...")
        self.page_modem.show_all()

    def on_test_touchscreen_clicked(self, *args):
        self.stack.set_visible_child(self.page_touchscreen)

    def on_tstest_click(self, button):
        self.tstest_clicked.add(button)
        button.get_style_context().add_class('suggested-action')
        if len(self.tstest_clicked) == 12:
            self.test_touchscreen.get_style_context().add_class('suggested-action')

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

    def on_yesno_no_clicked(self, *args):
        button = self.builder.get_object('test_{}'.format(self.yesno_button))
        button.get_style_context().add_class('destructive-action')
        button.get_style_context().remove_class('suggested-action')
        self.page_main.show_all()
        self.stack.set_visible_child(self.page_main)

    def on_test_earpiece_clicked(self, *args):
        self.run_yesno('earpiece', 'Does sound come out of the earpiece?')


def main():
    app = FactoryTestApplication("org.pine64.pinephone.factorytest", Gio.ApplicationFlags.FLAGS_NONE)
    app.run()


if __name__ == '__main__':
    main()
