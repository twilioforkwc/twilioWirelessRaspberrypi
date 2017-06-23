# coding: utf-8

'''Twilio Programmable Wireless Command using Raspberry Pi, Twilio Wireless SIM and ABIT AK-020
'''

import sys
import time
import serial
import re
import threading
import RPi.GPIO as GPIO
LED = 3 # ボード上の3番ピン(GPIO2)
BTN = 21 # ボード上の21番ピン(GPIO9)

class Board:

  # コンストラクタ
  def __init__(self):
    # ピンのモードをそれぞれ出力用と入力用に設定
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(LED, GPIO.OUT)
    GPIO.setup(BTN, GPIO.IN)
    self.ledoff()

  def ledon(self):
    # LEDを点ける
    GPIO.output(LED, GPIO.HIGH)

  def ledoff(self):
    # LEDを消す
    GPIO.output(LED, GPIO.LOW)

class Sms:
  # コンストラクタ
  def __init__(self):
    # SMSメッセージかどうかをチェックする文字列パターン
    self.pattern = re.compile('\+CMGL: [0-9]+,"REC UNREAD"')

    # シリアル通信の設定
    self.serial = serial.Serial(
      '/dev/ttyUSB0',
      460800,
      timeout = 5,
      xonxoff = False,
      rtscts = False,
      dsrdtr = False,
      bytesize = serial.EIGHTBITS,
      parity = serial.PARITY_NONE,
      stopbits = serial.STOPBITS_ONE
    )

    # ATZ：モデム初期化
    self.serial.write('ATZ\r')
    self.check_response_isok()
    # AT+CFUN：機能モードを設定（1:Full Functionaly）
    self.serial.write('AT+CFUN=1\r')
    self.check_response_isok()
    # AT+CGDCONT：APNの書き込み
    self.serial.write('AT+CGDCONT=1,"IP","wireless.twilio.com"\r')
    self.check_response_isok()
    # AT+CMGF：SMSを設定（1:テキストモード）
    self.serial.write('AT+CMGF=1\r')
    self.check_response_isok()

  # ディストラクタ
  def __del__(self):
    # シリアル通信を閉じる
    self.serial.close()

  # ウェイト
  def wait_response(self):
    time.sleep(1)
    while self.serial.inWaiting() == 0:
      time.sleep(0.5)

  # OK応答の確認
  def check_response_isok(self):
    self.wait_response()
    r = self.serial.read(self.serial.inWaiting()).split('\r\n')
    if len(r) < 2 or r[-2] != 'OK':
      raise Exception(r)

  # プロンプト応答の確認
  def check_response_isprompt(self):
    self.wait_response()
    r = self.serial.read(self.serial.inWaiting()).split('\r\n')
    if len(r) < 1 or r[-1] != '> ':
      raise Exception(r)

  # 読み捨て
  def dispose_response(self):
    self.wait_response()
    self.serial.read(self.serial.inWaiting())

  # メッセージの送信
  def send_message(self, message, to):
    self.serial.write('AT+CMGS="%s"\r' % to)
    self.check_response_isprompt()
    self.serial.write(message + chr(26)) # CTRL-Z
    self.dispose_response()
    self.check_response_isok()

  # メッセージの受信
  def receive_message(self):
    self.serial.write('AT+CMGL="REC UNREAD"\r\n')
    self.wait_response()
    r = self.serial.read(self.serial.inWaiting()).split('\r\n')

    if len(r) < 2 or r[-2] != 'OK':
      raise Exception(r)

    messages = []
    is_message = False

    for line in r:
      if is_message:
        messages.append(line)

      if line and self.pattern.match(line):
        is_message = True
      else:
        is_message = False

    return messages

class MainThread(threading.Thread):
    def __init__(self, n):
        super(MainThread, self).__init__()
        self.n = n

    def run(self):
        print " === start thread === "
        # 指定された回数だけ受信メッセージ取得をループ
        for i in range(self.n):
            messages = sms.receive_message()
            for message in messages:
                if message.upper() == 'ON':
                    board.ledon()
                elif message.upper() == 'OFF':
                    board.ledoff()
                print message

            before = 0
            # ボタンチェックループ（20 * 0.1秒）
            for i in range(20):
              # 押された場合には1、押されていない場合0を返す
              now = GPIO.input(BTN)
              if before == 0 and now == 1:
                sms.send_message('Push', '2936')
                print("Command sent.")
              time.sleep(0.1)
              before = now

        board.ledoff()
        print " === end thread === "

if __name__ == '__main__':
    board = Board()
    sms = Sms()
    th_main = MainThread(30) # 30 * ループ1回につき2秒 = 60秒間実行
    th_main.start()
