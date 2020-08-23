import os
import itchat, time
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "weight2.settings")
django.setup()


def lc():
    print("Finish Login!")


def ec():
    print("exit")


itchat.auto_login(loginCallback=lc, exitCallback=ec)

time.sleep(1000)
itchat.logout()    #强制退出登录
