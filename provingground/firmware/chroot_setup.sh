#!/bin/bash
#
# Wrapper script to create a new chroot
#

usage()
{
cat <<EOF
  Usage: $0 -d {DIR} [ -b {BRANCH} ] [ -s {BOARD} ]
  -d {DIR}    a non-existing directory to create repo
  -b {BRANCH} optional: will create BRANCH_NAME repo
  -s {BOARD}  optional: will setup and build BOARD_NAME

  Example:
  To setup a new repo at head on /disk2:
    ./chroot_setup.sh -d /disk2/chromiumos

  To setup at head on /disk2 and build board tidus :
    ./chroot_setup.sh -d /disk2/chromiumos -s tidus

  To setup branch firmware-tidus-6301.109.B on /disk2 and build board tidus :
    ./chroot_setup.sh -d /disk2/firmware-tidus-6301.109.B -b firmware-tidus-6301.109.B -s tidus

  To cleanup branch created in /disk2/chromiumos:
    cd /disk2/chromiumos; cros_sdk --delete
    cd /; sudo rm -rf /disk2/chromiumos
EOF
}

DIR=""
BRANCH=""
BOARD=""
while getopts d:b:s: opt
do
  case "$opt" in
    d) DIR=$2; shift 2;;
    b) BRANCH=$2; shift 2;;
    s) BOARD=$2; shift 2;;
    *) usage; exit 1;;
  esac
done
if [ -z "$DIR" ]; then
  echo Missing -d option
  usage
  exit 1
fi

if [ -d $DIR ]; then
  echo Directory $DIR already exist. Cannot create new repo $DIR.
  exit 1
fi


# so you can do sudo later without asking password.
sudo echo

# Print each command as they executed
set -x
# Script exit on any command exit with non zero status
set -e

BRANCH_OPT=""
if [ "$BRANCH" != "" ]; then
  BRANCH_OPT="-b $BRANCH"
fi

mkdir -p $DIR
cd $DIR

date
repo init \
  -u https://chrome-internal.googlesource.com/chromeos/manifest-internal.git \
  $BRANCH_OPT \
  --repo-url=https://chromium.googlesource.com/external/repo.git \
  > repo_init.out 2>&1

date
repo sync > repo_sync.out 2>&1

date
cros_sdk -- exit

# remove bash logout clear screen
rm $DIR/chroot/home/$USER/.bash_logout

# personalize shell
cat <<EOF >> $DIR/chroot/home/$USER/.bash_profile
# export PS1='\${HOME}:\W\$(__git_ps1 "(%s)") \u \$ '
export PS1='\033]2;\h[\${TTY}]\${PWD}\007\n$DIR:\W\$(__git_ps1 "(%s)") \u \$ '
# use the right editor
export EDITOR=vi
# do not clear screen on exit
export LESS=”-XF”
export PAGER=more
# useful aliases
alias ls='ls -CF'
alias ll='ls -l'
alias l.='ls -dl .??*'
alias h='history'
alias rm='rm -i'
alias is='ps axuwwww | grep'
alias tt='test_that --autotest_dir ~/trunk/src/third_party/autotest/files/'
EOF

cat <<EOF >> $DIR/chroot/home/$USER/.vimrc
" no warp in seach
set nowrapscan
" no highlight in search
set hlsearch!
set shiftwidth=4
set tabstop=4
EOF

if [ -z "$BOARD" ]; then
  echo repo $DIR setup done.
  exit 0
fi

date
cros_sdk -- ./setup_board --board=$BOARD > setup_board.out 2>&1

date
cros_sdk -- ./build_packages --board=$BOARD > build_packages.out 2>&1

date
echo DONE.
exit 0
