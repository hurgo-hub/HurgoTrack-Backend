#!/bin/sh
# Programa los respaldos en el crontab del usuario del VPS (sin sudo). Se puede
# correr varias veces: reemplaza solo el bloque marcado "hurgotrack-backup".
# Hora del servidor (UTC). El snapshot de Contabo corre a las 03:00.
set -eu
B="$HOME/HurgoTrack/backend/deploy/backup/backup.sh"
LOG="$HOME/HurgoTrack/backups.log"

BLOCK="# >>> hurgotrack-backup
15 2 * * 0   $B full         >> $LOG 2>&1
15 2 * * 1-6 $B diff         >> $LOG 2>&1
45 2 * * *   $B media        >> $LOG 2>&1
30 4 * * 0   $B check        >> $LOG 2>&1
30 5 1 * *   $B restore-test >> $LOG 2>&1
# <<< hurgotrack-backup"

current="$(crontab -l 2>/dev/null || true)"
cleaned="$(printf '%s\n' "$current" | sed '/^# >>> hurgotrack-backup$/,/^# <<< hurgotrack-backup$/d')"
printf '%s\n%s\n' "$cleaned" "$BLOCK" | sed '/./,$!d' | crontab -
echo "Crontab actualizado:"
crontab -l | sed -n '/^# >>> hurgotrack-backup$/,/^# <<< hurgotrack-backup$/p'
