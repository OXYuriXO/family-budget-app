[app]

title = Бюджет семьи
package.name = budget
package.domain = org.family

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy==2.3.1,openpyxl,et-xmlfile

orientation = portrait
fullscreen = 0

# Чтобы задать свою иконку — положите icon.png (квадратный, напр. 512x512)
# в эту же папку и раскомментируйте строку ниже.
# icon.filename = %(source.dir)s/icon.png

android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.api = 34
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a, armeabi-v7a

[buildozer]

log_level = 2
warn_on_root = 1
