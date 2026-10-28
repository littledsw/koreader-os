#!/bin/sh
# Kobo 硬件/系统探测脚本（M0）
# 用法（在已开 SSH 的 Kobo 上）：
#   sh probe.sh > /mnt/onboard/hardware-profile.txt 2>&1
# 然后把 hardware-profile.txt 拷回电脑。
# 只读，不改任何东西。

echo "=== date ==="
date 2>/dev/null

echo "=== uname ==="
uname -a 2>/dev/null

echo "=== version file ==="
cat /mnt/onboard/.kobo/version 2>/dev/null
cat /etc/version 2>/dev/null

echo "=== cpuinfo ==="
cat /proc/cpuinfo 2>/dev/null

echo "=== cmdline ==="
cat /proc/cmdline 2>/dev/null

echo "=== mem ==="
cat /proc/meminfo 2>/dev/null | head -n 5
free 2>/dev/null

echo "=== partitions ==="
cat /proc/partitions 2>/dev/null

echo "=== block devices ==="
ls -l /dev/mmcblk* /dev/loop* 2>/dev/null

echo "=== mounts ==="
mount 2>/dev/null
cat /proc/mounts 2>/dev/null | head -n 40

echo "=== modules ==="
lsmod 2>/dev/null
ls /lib/modules 2>/dev/null
ls /lib/modules/*/ 2>/dev/null | head -n 80

echo "=== firmware ==="
ls /lib/firmware 2>/dev/null | head -n 40

echo "=== framebuffer ==="
for f in /sys/class/graphics/fb0/bits_per_pixel \
         /sys/class/graphics/fb0/virtual_size \
         /sys/class/graphics/fb0/stride \
         /sys/class/graphics/fb0/modes \
         /sys/class/graphics/fb0/name \
         /sys/class/graphics/fb0/rotate; do
  echo -n "$f: "; cat "$f" 2>/dev/null; echo
done

echo "=== input devices ==="
cat /proc/bus/input/devices 2>/dev/null
ls -l /dev/input/ 2>/dev/null

echo "=== backlight / frontlight ==="
ls /sys/class/backlight/ 2>/dev/null
for d in /sys/class/backlight/*; do
  echo "-- $d"
  cat "$d/max_brightness" 2>/dev/null
  cat "$d/brightness" 2>/dev/null
done
ls /sys/class/leds/ 2>/dev/null | head -n 20

echo "=== power ==="
cat /sys/power/state 2>/dev/null
ls /sys/class/power_supply/ 2>/dev/null
for d in /sys/class/power_supply/*; do
  echo "-- $d"
  cat "$d/capacity" 2>/dev/null
  cat "$d/status" 2>/dev/null
done

echo "=== thermal ==="
ls /sys/class/thermal/ 2>/dev/null

echo "=== wifi ==="
ls /sys/class/net/ 2>/dev/null
cat /proc/net/wireless 2>/dev/null
ls /etc/wpa_supplicant* 2>/dev/null

echo "=== kobo userspace ==="
ls /usr/local/Kobo/ 2>/dev/null | head -n 40
ls /usr/local/Kobo/lib 2>/dev/null | head -n 40
ls /etc/init.d/ 2>/dev/null

echo "=== nickel start ==="
grep -n "nickel" /etc/init.d/rcS 2>/dev/null

echo "=== u-boot env ==="
which fw_printenv 2>/dev/null
fw_printenv 2>/dev/null | head -n 40

echo "=== koreader ==="
ls /mnt/onboard/.adds 2>/dev/null
ls /mnt/onboard/.adds/koreader 2>/dev/null | head -n 10

echo "=== storage ==="
df -h 2>/dev/null
ls -l /mnt/onboard 2>/dev/null | head -n 20
ls /mnt/sd 2>/dev/null | head -n 10

echo "=== done ==="
