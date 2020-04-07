import os
import time
from subprocess import Popen, PIPE

PROFILEDIR=os.path.abspath("C:\WiFiXML")
os.makedirs(PROFILEDIR, exist_ok=True)
logger = open(os.path.join(PROFILEDIR, "WiFi_logs.txt"), "a")

def get_time():
    return time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())

def filter_profiles(info:dict, option:str="secured"):
    assert isinstance(info, dict), f"filter_dict Invalid Type: Expecting type(dict) but {type(info)} provided"
    auth = option.lower() == 'secured'
    signal = option.lower() in ['good', 'strong', 'strength']
    filtered = {}
    max_signal = 0
    for key, val in info.items():
        sec = val.get('Authentication').lower()
        if auth & ( sec != 'open' ):
            filtered.update({key: val})

        best = val.get('Signal').strip('%')        
        try:
            best = float(best)
        except Exception as Ex:
            log_info("Couldn't Convert", best, 'from', {key: val}, Ex)
            continue
        max_signal = max_signal if max_signal > best else best
    
    if signal:
        for key, val in info.items():
            best = val.get('Signal').strip('%')
            if best == str(max_signal):
                filtered.update({key: val})
                break
    return filtered
               
def log_info(*args):
    global logger
    text = ",".join(str(arg) for arg in args)
    if logger.closed:
        logger  = open(os.path.join(PROFILEDIR, "WiFi_logs.txt"), "a")
    logger.write(f"{get_time()},{text}\n")
    print(get_time(), text)
    return

def get_files():
    files = dict((name.replace("Wi-Fi-", "").replace(".xml", ""), os.path.join(PROFILEDIR, name)) for name in os.listdir(PROFILEDIR) if name.endswith('.xml'))
    return files
    
def cmd(*args):
    process = Popen([*args], stdout=PIPE, stderr=PIPE, shell=True)
    out, err = process.communicate()
    output = err + out
    text = ""
    try:
        text = output.decode('utf-8')
    except:
        for byte in output:
            try:
                byte = chr(byte)
            except Exception as EX:
                byte = ""
            text += byte   
    #print("TEXT:", text.split('\r\n'))
    return text

def get_profiles():
    profiles = list()
    log_info("Wi-Fi Getting Wireless Profiles ...")
    text = cmd("netsh", "wlan", "show", "profiles")
    if "All User Profile" in text:
        for line in text.split('\r\n'):
            if "All User Profile" in line:
                idx = line.find(":")
                if idx > -1:
                    ssid = line[idx + 1:].strip()
                    if ssid: profiles.append(ssid)
    log_info(f"Available Wireless Profiles are {profiles}")
    return profiles

def connect_profile(profile):
    log_info(f"Wi-Fi Connecting to {profile} ...")
    text = cmd("netsh", "wlan", "connect", f"name={profile}", f"ssid={profile}")
    time.sleep(5)
    checked = "request was completed successfully" in text or profile == get_connected_profile()
    return checked

def get_connected_profile():
    wifi = ""
    log_info("Wi-Fi Getting Connected Profile ...")
    text = cmd("netsh", "wlan", "show", "interfaces", "|", "findstr", "SSID")
    if "SSID" in text:
        for line in text.split('\r\n'):
            words = [ word.strip() for word in line.split(':') if word ]
            if "SSID" in words:
                wifi = words[-1]
                break
    log_info(f"Wi-Fi Connected Network Found is '{wifi}'.")
    return wifi

def get_interface_info():
    info = dict()
    log_info("Wi-Fi Getting Interface Information ...")
    text = cmd("netsh", "wlan", "show", "interfaces")
    text = [line.strip() for line in text.split('\r\n') if line]
    indexes = [idx for idx, line in enumerate(text) if line.startswith("Name")]
    end = len(text)
    stop = len(indexes)
    for pos, idx in enumerate(indexes):
        if pos + 1 < stop: 
            items = list((tuple(line.split(':', 1)) for line in text[idx:indexes[pos + 1]]))
        else:
            items = list((tuple(line.split(':', 1)) for line in text[idx:]))
        temp = dict((key.strip(), val.strip()) for key, val, *extra in items)
        info.update({temp.get('Profile'): temp})
    log_info("Wi-Fi Connected Interface info", info)
    return info

def delete_profile(profile):
    log_info(f"Wi-Fi Deleting profile: {profile}")
    text = cmd("netsh", "wlan", "delete", "profile", f"name={profile}").strip()
    checked = "is deleted from interface" in text or profile not in get_profiles()
    return checked

def add_profile(profile):
    if not os.path.isfile(profile):
        files = get_files()
        if files:
            profile = files.get(profile) # Getting profile's file 
    log_info(f"Wi-Fi Adding profile: {profile}")
    text = cmd("netsh", "wlan", "add", "profile", f"filename={profile}", "user=all")
    checked = "is added on interface" in text or profile in get_profiles()
    return checked
   
def backup_profiles():
    text = cmd("netsh", "wlan", "export", "profile", "key=clear", f"folder={PROFILEDIR}")
    if "successfully" not in text:
        return False
    else:
        saved = [line for line in text.split('\r\n') if line]
        found = get_profiles()
        ret = len(saved) == len(found)
        return ret
    
def delete_profiles():
    if backup_profiles():
        profiles = get_profiles()
        log_info("Deleting All Wi-Fi profiles", profiles)
        for profile in profiles:
            delete_profile(profile)
    return len(get_profiles()) == 0

def restore_profiles():
    files = get_files()
    found = get_profiles()
    log_info("Restoring Profiles", files)
    for profile in files:
        if profile not in found: 
            add_profile(profile)
    found = get_profiles()
    checked = [profile in found for profile in files]
    if all(checked):
        log_info("Wi-Fi Profiles Restored", files, found)
    else:
        log_info("Wi-Fi Unabled to restore profiles")
    return all(checked)

def get_networks():
    networks = list()
    text = cmd("netsh", "wlan", "show", "networks", "|", "findstr", "SSID")
    if "SSID" in text:
        for line in text.split('\r\n'):
            idx = line.find(":")
            if idx > -1:
                ssid = line[idx + 1:].strip()
                if ssid: networks.append(ssid)
    log_info("Available Wi-Fi Networks", networks)
    return networks

def connect_suitable_profile():
    log_info("Wi-Fi Connecting Suitable Network ...")
    suitable = ""
    profiles = get_profiles()
    networks = get_networks()
    possibles = [wifi for wifi in profiles if wifi in networks]
    if possibles:
        print("Suitable Profiles", possibles)
        if len(possibles) == 1:
            suitable = possibles[-1]
        else:
            suitables = dict()
            for profile in possibles:
                if connect_profile(profile):
                    suitables.update(get_interface_info())
            print("\nPROFILES:\n", suitables)
            strong = filter_profiles(suitables, "good")
            if strong:
                for profile, info in strong.items():
                    if info.get().lower() == 'open':
                        suitable = profile
            if suitable == "":
                secured = filter_profiles(suitables)
                strong = filter_profiles(secured)
                if strong:
                    for profile, info in strong.items():
                        suitable = profile
                elif secured:
                    for profile, info in secured.items():
                        suitable = profile
                        break
        log_info(f"\tWi-Fi Suitable Profile is {suitable}")
    else:
        log_info("\tPlease Connect to a Network")
        input("Press Enter to Continue ...")
    return suitable

def get_target_profile():
    thiswifi = get_connected_profile() or connect_suitable_profile()
    profiles = get_profiles() + get_networks()
    checked = thiswifi not in profiles
    while checked:
        time.sleep(5)
        profiles = get_profiles() + get_networks()
        if thiswifi == "":
            thiswifi = get_connected_profile() or connect_suitable_profile()
        checked = thiswifi not in profiles
    log_info(f"Target Wifi is {thiswifi}")   
    return thiswifi
    
def loop_auto_reconnect():
    target = get_target_profile()
    log_info(f"Wi-Fi Target Profile is {target}")
    if backup_profiles():
        log_info("Wi-Fi Profiles Backed up", get_files())
        try: 
            while True:
                connected = get_connected_profile()
                if connected != target:
                    log_info(f"Wi-Fi is Diconnected from {target}")
                    delete_profile(target)
                    time.sleep(3)
                    if add_profile(target):
                        connect_profile(target)
                    continue
                else:
                    log_info(f"Wi-Fi Connected to: {connected}")
                time.sleep(30)
        except KeyboardInterrupt:
            log_info("!! Interrupted !!")
        restore_profiles()
    else:
        try:
            while True:
                connected = get_connected_profile() or connect_suitable_profile()
                if connected != target:
                    log_info(f"Wi-Fi is disconnected {target}")
                    if connect_profile(target):
                        log_info(f"Wi-Fi Reconnected to {target}")
                time.sleep(10)
        except KeyboardInterrupt:
            log_info("!! Interrupted !!")
    return

if __name__ == "__main__":
    logger.write(f"\n\n{get_time()}\tStarting Wi-Fi Auto-Reconnect ...\n\n")
    loop_auto_reconnect()
    logger.write(f"\n{get_time()}\Exiting Wi-Fi Auto-Reconnect ...\n")
    # connect_suitable_profile()
