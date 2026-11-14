#!/usr/bin/env python3
"""Put vince-uicache into the iOS root and run it once at boot.

  sudo python3 install.py ROOT BINARY            # ROOT = mounted iOS root, BINARY = vince-uicache from the workflow
  sudo python3 install.py ROOT --undo

Adds ROOT/usr/local/bin/vince-uicache and one launchd job com.vince.uicache (RunAtLoad, output to /dev/console).
The program stops itself after the first run (marker /var/mobile/.vince-uicache); delete the marker to run again.
"""
import os, plistlib, shutil, sys

LABEL = 'com.vince.uicache'
BIN = 'usr/local/bin/vince-uicache'
PLIST = 'System/Library/xpc/launchd.plist'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    undo = '--undo' in sys.argv
    if not args or not os.path.isdir(os.path.join(args[0], 'System/Library/xpc')) or (not undo and len(args) != 2):
        sys.exit(__doc__)
    root = args[0]
    plist_path = os.path.join(root, PLIST)
    st = os.stat(plist_path)
    with open(plist_path, 'rb') as f:
        plist = plistlib.load(f)
    jobs = plist['LaunchDaemons']
    for key in [k for k, j in jobs.items() if j.get('Label') == LABEL]:
        del jobs[key]
    dst = os.path.join(root, BIN)
    if undo:
        if os.path.exists(dst):
            os.remove(dst)
    else:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(args[1], dst)
        os.chmod(dst, 0o755)
        try:
            os.chown(dst, 0, 0)
        except PermissionError:
            print('warning: not root, owner not set')
        jobs['/System/Library/LaunchDaemons/%s.plist' % LABEL] = {
            'Label': LABEL,
            'ProgramArguments': ['/' + BIN],
            'RunAtLoad': True,
            'KeepAlive': False,
            'StandardOutPath': '/dev/console',
            'StandardErrorPath': '/dev/console',
            'UserName': 'mobile',
            'EnablePressuredExit': False,
            'EnableTransactions': False,
        }
    backup = plist_path + '.vince-uicache-orig'
    if not os.path.exists(backup):
        shutil.copyfile(plist_path, backup)
    with open(plist_path, 'wb') as f:
        plistlib.dump(plist, f, fmt=plistlib.FMT_BINARY)
    os.chmod(plist_path, st.st_mode & 0o7777)
    print(('removed' if undo else 'installed') + ' ' + LABEL)


if __name__ == '__main__':
    main()
