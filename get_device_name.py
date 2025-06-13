import subprocess
import os
import sys


def resource_path(relative_path):
    """ Get absolute path to resource (works with PyInstaller) """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_connected_devices():
    try:
        location = resource_path(".\\adb\\adb.exe")
        output = subprocess.check_output([location, 'devices'], encoding='utf-8')
        lines = output.strip().split('\n')[1:]
        devices = [line.split()[0]for line in lines if 'device' in line and not 'unauthorized' in line]
        return devices
    except Exception:
        return []

def get_device_name(device_id=None):
    try:
        cmd = resource_path(".\\adb\\adb.exe")
        if device_id:
            cmd += ['-s', device_id]
            cmd += ['shell', 'getprop','ro.product.model']
            output = subprocess.check_output(cmd, encoding='utf-8')
            return output.strip()
    except:
        return "Error while getting device name"

