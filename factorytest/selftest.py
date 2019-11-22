import time
import smbus
from statistics import mean


def _read_i2c_word():
    pass


def mpu6050(bus=1, address=0):
    bus = smbus.SMBus(bus)

    # Set accel-config to self-test, 8g
    bus.write_byte_data(address, 0x1c, 0xf0)

    # Set gyro-config to self-test, 250deg/s
    bus.write_byte_data(address, 0x1b, 0xe0)

    # Wait for chip to run self-test
    time.sleep(0.25)

    # Read test results
    self_text_x = bus.read_byte_data(address, 0x0d)
    self_text_y = bus.read_byte_data(address, 0x0e)
    self_text_z = bus.read_byte_data(address, 0x0f)
    self_text_a = bus.read_byte_data(address, 0x10)

    result_accel_x = (self_text_x >> 3) | (self_text_a & 0x30) >> 4
    result_accel_y = (self_text_y >> 3) | (self_text_a & 0x0c) >> 2
    result_accel_z = (self_text_z >> 3) | (self_text_a & 0x03) >> 0

    result_gyro_x = self_text_x & 0x1f
    result_gyro_y = self_text_y & 0x1f
    result_gyro_z = self_text_z & 0x1f

    # Read the factory trim values
    trim_accel_x = (4096 * 0.34) * pow((0.92 / 0.34), (float(result_accel_x) - 1.0 / 30.0))
    trim_accel_y = (4096 * 0.34) * pow((0.92 / 0.34), (float(result_accel_y) - 1.0 / 30.0))
    trim_accel_z = (4096 * 0.34) * pow((0.92 / 0.34), (float(result_accel_z) - 1.0 / 30.0))
    trim_gyro_x = (25.0 * 131.0) * pow(1.046, float(result_gyro_x) - 1.0)
    trim_gyro_y = (-25.0 * 131.0) * pow(1.046, float(result_gyro_y) - 1.0)
    trim_gyro_z = (25.0 * 131.0) * pow(1.046, float(result_gyro_z) - 1.0)

    # Check if error is within manufacturer tolerance
    error_accel_x = 100.0 + 100.0 * (float(result_accel_x) - trim_accel_x) / trim_accel_x
    error_accel_y = 100.0 + 100.0 * (float(result_accel_y) - trim_accel_y) / trim_accel_y
    error_accel_z = 100.0 + 100.0 * (float(result_accel_z) - trim_accel_z) / trim_accel_z
    error_gyro_x = 100.0 + 100.0 * (float(result_gyro_x) - trim_gyro_x) / trim_gyro_x
    error_gyro_y = 100.0 + 100.0 * (float(result_gyro_y) - trim_gyro_y) / trim_gyro_y
    error_gyro_z = 100.0 + 100.0 * (float(result_gyro_z) - trim_gyro_z) / trim_gyro_z
    max_error = max(error_accel_x, error_accel_y, error_accel_z, error_gyro_x, error_gyro_y, error_gyro_z)

    print("MPU-6050 error is {}%".format(max_error))

    # Maximum error in the datasheet is 14%
    return max_error < 14


def lis3mdl(bus=1, address=0x1e):
    bus = smbus.SMBus(bus)

    def read_sample():
        dataready = False
        # Wait for data-ready bits
        for _ in range(0, 200):
            status = bus.read_byte_data(address, 0x27)
            dataready = status & 0x08
            if dataready:
                break
            time.sleep(0.01)
        if not dataready:
            raise Exception('LIS3MDL timeout')

        out_x = bus.read_byte_data(address, 0x28)
        out_x |= bus.read_byte_data(address, 0x29) << 8
        out_y = bus.read_byte_data(address, 0x2a)
        out_y |= bus.read_byte_data(address, 0x2b) << 8
        out_z = bus.read_byte_data(address, 0x2c)
        out_z |= bus.read_byte_data(address, 0x2d) << 8

        x = out_x if out_x < 32768 else (out_x - 65536)
        y = out_y if out_y < 32768 else (out_y - 65536)
        z = out_z if out_z < 32768 else (out_z - 65536)
        return x / 2281.0, y / 2281.0, z / 2281.0

    # Configure 12 Gauss range, continious measurement, 80 Hz mode
    bus.write_byte_data(address, 0x20, 0x1c)
    bus.write_byte_data(address, 0x21, 0x40)
    time.sleep(0.02)
    bus.write_byte_data(address, 0x22, 0x00)
    time.sleep(0.02)

    # Discard first sample
    read_sample()

    # Read 5 samples averaged
    sample_x = []
    sample_y = []
    sample_z = []
    for i in range(0, 5):
        x, y, z = read_sample()
        sample_x.append(x)
        sample_y.append(y)
        sample_z.append(z)
    avg_x = mean(sample_x)
    avg_y = mean(sample_y)
    avg_z = mean(sample_z)

    # Enable self-test
    bus.write_byte_data(address, 0x20, 0x1d)
    time.sleep(0.06)

    # Discard first sample
    read_sample()

    # Read 5 samples averaged
    sample_x = []
    sample_y = []
    sample_z = []
    for _ in range(0, 5):
        x, y, z = read_sample()
        sample_x.append(x)
        sample_y.append(y)
        sample_z.append(z)
    avg_x_test = mean(sample_x)
    avg_y_test = mean(sample_y)
    avg_z_test = mean(sample_z)

    # Verify test result
    res_x = avg_x_test - avg_x
    res_y = avg_y_test - avg_y
    res_z = avg_z_test - avg_z
    print("RESULT: {} {} {}".format(res_x, res_y, res_z))
    ok = 0
    if 1.0 <= abs(res_x) <= 3.0:
        ok += 1
    if 1.0 <= abs(res_y) <= 3.0:
        ok += 1
    if 0.1 <= abs(res_z) <= 1.0:
        ok += 1

    # Disable self-test
    bus.write_byte_data(address, 0x20, 0x1c)

    return ok == 3
