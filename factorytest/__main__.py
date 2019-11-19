import threading

import gi
import logging
import glob
import os

try:
    import importlib.resources as pkg_resources
except ImportError:
    import importlib_resources as pkg_resources

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GObject, Gio, GdkPixbuf

logging.basicConfig(level=logging.DEBUG)


class AutoTests(threading.Thread):
    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.callback = callback

    def run(self):
        GLib.idle_add(self.callback, ['Testing MPU-6050', 0, None])
        result = self.test_sensor('mpu6050', 'in_accel_x_raw')
        GLib.idle_add(self.callback, ['Testing LIS3MDL', 1, ('sixaxis', result)])
        result = self.test_sensor('lis3mdl', 'in_magn_x_raw')
        GLib.idle_add(self.callback, ['Testing STK3335', 2, ('magnetometer', result)])
        result = self.test_sensor('stk3310', 'in_proximity_raw')
        GLib.idle_add(self.callback, ['Testing RTL8723CS', 3, ('proximity', result)])

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

        # Stack pages
        self.page_main = builder.get_object('page_main')
        self.page_progress = builder.get_object('page_progress')

        # Progress page
        self.progress_status = builder.get_object('progress_status')
        self.progress_bar = builder.get_object('progress_bar')
        self.progress_log = builder.get_object('progress_log')

    def on_quit(self, *args):
        Gtk.main_quit()

    def on_test_auto_clicked(self, *args):
        self.stack.set_visible_child(self.page_progress)
        thread = AutoTests(self.autotests_update)
        thread.start()

    def autotests_update(self, result):
        self.progress_status.set_text(result[0])
        fraction = result[1] / 7.0
        self.progress_bar.set_fraction(fraction)

        update = result[2]
        if update is not None:
            ob = self.builder.get_object('result_' + update[0])
            if update[1]:
                ob.set_text('OK')
            else:
                ob.set_text('failed')

        self.page_progress.show_all()


def main():
    app = FactoryTestApplication("org.pine64.pinephone.factorytest", Gio.ApplicationFlags.FLAGS_NONE)
    app.run()


if __name__ == '__main__':
    main()
