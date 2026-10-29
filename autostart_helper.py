import winreg
import sys
import os

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "SapXepFile_AutoOrganizer"

def set_autostart(enable: bool, exe_path: str = None) -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        if enable:
            if not exe_path:
                exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
            # Chạy kèm tham số --background
            cmd = f'"{exe_path}" --background'
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Lỗi cấu hình khởi động cùng Windows: {e}")
        return False

def check_autostart() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False

if __name__ == "__main__":
    print("Autostart check:", check_autostart())
