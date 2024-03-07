# .bashrc

# If not running interactively, don't do anything
[ -z "$PS1" ] && return

# don't put duplicate lines in the history. See bash(1) for more options
# ... or force ignoredups and ignorespace
HISTCONTROL=ignoredups:ignorespace

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "$debian_chroot" ] && [ -r /etc/debian_chroot ]; then
  debian_chroot=$(cat /etc/debian_chroot)
fi

# Color prompt
if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
  if [[ $EUID -ne 0 ]]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[0;96m\][\D{%F %T}]\[\033[0m\] \[\033[34m\]\u\[\033[35m\]@\h\[\033[0m\]:\[\033[96m\]\w\[\033[0m\]\n\$ '
  else
    PS1='\[\033[0;96m\][\D{%F %T}] \033[1;31m\]\u@\h:\w\[\033[0m\]\n\$ '
  fi
else
  PS1='${debian_chroot:+($debian_chroot)]}[\D{%F %T}] \u@\h:\w\n\$ '
fi

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable bash completion in interactive shells
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
  test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
  alias ls='ls --time-style=long-iso --color=auto'

  alias grep='grep --color=auto'
  alias fgrep='fgrep --color=auto'
  alias egrep='egrep --color=auto'
else
  alias ls='ls --time-style=long-iso'
fi

alias dt='date +%F\ %T\ %Z\ -\ w%V\ %A'

if [ -f ~/.aliasses.sh ]; then
  . ~/.aliasses.sh
fi
if [ -f ~/.local/aliasses.sh ]; then
  . ~/.local/aliasses.sh
fi

# Activate Python virtual environment
if [[ -d ~/.venv ]]; then
  . ~/.venv/bin/activate
fi

