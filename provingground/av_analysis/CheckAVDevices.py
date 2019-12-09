#!/usr/bin/env python3

import json
import os
import sys
import subprocess

from time import time
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

from common.cmd_helper import *
from common.av_helper import *

# Globals
_menu_items = [
    'ping_recorders',
    'prep_host_for_ssh',
    'ssh_to_rec',
    'update_full_server'
    'update_servlet',
    'create_test_recording',
    'get_recorder_status',
]
_cros = '.cros'
_recorder = '-recorder'
_FNULL = open(os.devnull, 'w')


def load_active_duts():
    with open('all_duts.json') as file:
        data = json.load(file)
        return data['active']


def main(argv):

    session = PromptSession()
    menu_completer = WordCompleter(_menu_items, ignore_case=True)

    while True:
        try:
            choice = session.prompt('Main Menu > ', completer=menu_completer)
            choice = choice.lower()
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        else:
            for host in load_active_duts():
                # globals()[choice]() lets us call the appropriate method
                # with str value instead of hard identifier.
                globals()[choice](host)
    print('GoodBye!')


def print_help():
    print('Type in one of the following options into the prompt:')
    for item in _menu_items:
        print(' - ' + item)
    print('Or hit Ctrl + D to exit.')


def ping_recorders(host):
    rec_name = host + _recorder + _cros
    rec_ping_args = ['ping', '-c', '1', rec_name]
    response = subprocess.call(rec_ping_args, stdout=_FNULL)
    print("REC: {0:50} Ping Result: {1}".format(rec_name, response))


def update_servlet(host):
    rec_name = host + _recorder + _cros
    filename = 'servlet.py'
    src_filepath = os.path.join(os.getcwd(), 'recording_server', filename)
    dst_filepath = os.path.join('~', 'servlet', filename)
    scp_destination = 'root@{0}:{1}'.format(rec_name, dst_filepath)

    scp_args = ['scp',
                src_filepath,
                scp_destination]
    subprocess.call(scp_args, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)


def update_full_server(host):
    rec_name = host + _recorder + _cros
    ssh_destination = 'root@{0}'.format(rec_name)
    src_filepath = os.path.join(os.getcwd(), 'recording_server')
    dst_filepath = os.path.join('~', 'recording_server')
    scp_destination = '{0}:{1}'.format(ssh_destination, dst_filepath)

    del_args = ['ssh',
                ssh_destination,
                "rm -r recording_server"]
    subprocess.call(del_args)

    scp_args = ['scp',
                '-r',
                src_filepath,
                scp_destination]
    subprocess.call(scp_args)


def ssh_to_rec(host):
    rec_name = host + _recorder + _cros
    ssh_destination = 'root@' + rec_name
    ssh_args = 'gnome-terminal --tab -- ssh ' + ssh_destination
    subprocess.call(ssh_args, shell=True)


def create_test_recording(host):
    rec_name = host + _recorder + _cros

    # Hygiene
    video_device = get_vid_device()
    cmd = 'lsof -t {0}'.format(video_device)
    proc = None
    proc = run_remotely(cmd=cmd,
                        host=rec_name,
                        title='Checkig Video Device',
                        print_output=False,
                        process_error_okay=True)
    if proc is not None:
        kill_cmd = 'kill -9 {0}'.format(proc)
        run_remotely(cmd=kill_cmd,
                     host=rec_name,
                     title='Killing proc using video device.',
                     print_output=False,
                     process_error_okay=False)
    run_remotely(cmd=get_module_remove_cmd(), host=rec_name,
                 title='Remove Modules', print_output=True,
                 process_error_okay=False)
    run_remotely(cmd=get_module_add_cmd(), host=rec_name,
                 title='Add Modules', print_output=True,
                 process_error_okay=False)

    # Audio recording.
    audio_file = 'audio_test_{0}.wav'.format(str(int(time())))
    audio_cmd = 'ffmpeg -f alsa -i hw:1 -t 10 {0}'.format(audio_file)
    run_remotely(cmd=audio_cmd, host=rec_name,
                 title='AUDIO RECORDING', print_output=True,
                 process_error_okay=False)
    copy_from_remote(host=rec_name,
                     source_name=audio_file,
                     destination_name=audio_file)

    # Video recording.
    video_file = 'video_test_{0}.mp4'.format(str(int(time())))
    video_cmd = 'ffmpeg -f video4linux2 -s 1920x1080 -r 60 -i '\
                '/dev/video0 -f alsa -i hw:1 -qscale 2 -t 10 '\
                '-strict experimental -acodec aac -vcodec libx264 '\
                '-pix_fmt yuv420p -loglevel debug -y {0}'\
                .format(video_file)
    run_remotely(cmd=video_cmd, host=rec_name,
                 title='VIDEO RECORDING', print_output=True,
                 process_error_okay=False)
    copy_from_remote(host=rec_name,
                     source_name=video_file,
                     destination_name=video_file)


def get_recorder_status(host):
    rec_name = host + _recorder + _cros

    os_ver_cmd = 'hostnamectl'
    run_remotely(cmd=os_ver_cmd, host=rec_name,
                 title='OS VERSION', print_output=True,
                 process_error_okay=False)

    run_remotely(cmd=get_path_command(), host=rec_name,
                 title='PATH', print_output=True,
                 process_error_okay=False)

    run_remotely(cmd=get_ffmpeg_ver_cmd(), host=rec_name,
                 title='FFMPEG VERSION', print_output=True,
                 process_error_okay=False)

    run_remotely(cmd=get_video_devices_cmd(), host=rec_name,
                 title='VIDEO DEVICES', print_output=True,
                 process_error_okay=False)

    run_remotely(cmd=get_audio_devices_cmd(), host=rec_name,
                 title='AUDIO DEVICES', print_output=True,
                 process_error_okay=False)


def prep_host_for_ssh(host):
    rec_name = host + _recorder + _cros
    ssh_destination = 'root@' + rec_name
    cmd_args = 'gnome-terminal --tab -- ssh-copy-id -i ~/.ssh/id_rsa.pub ' + \
               ssh_destination
    subprocess.call(cmd_args, shell=True)


def get_ssh_args(device_name):
    ssh_args = ['ssh',
                'root@{0}'.format(device_name)]
    return ssh_args


def execute_command(args_list, title=None, new_tab=False):
    if title is not None:
        print('\n\n{0}:\n'.format(title))
    try:
        subprocess.check_output(args_list)
    except subprocess.CalledProcessError:
        print('Caught CalledProcessError. \n')


if __name__ == '__main__':
    main(sys.argv)

'''
Things that I still need to figure out:
- How to check if ffmpeg is installed on the system.
- How to check if the serverlet is running on the system.
'''
