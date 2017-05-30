from datetime import timedelta
from blinkstick import blinkstick
from PyQt5.QtWidgets import (QMainWindow, QLCDNumber, QWidget, QGridLayout, QApplication, QAction,  QStyle,
                             QLineEdit, QLabel, QVBoxLayout, QHBoxLayout)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtMultimedia import QSound
from threading import Thread
import sys


'''
    There are six steps in the technique:

    - Decide on the task to be done.
    - Set the pomodoro timer (traditionally to 25 minutes).[1]
    - Work on the task until the timer rings. If a distraction pops into your head, write it down, but immediately get
    back on task.
    - After the timer rings, put a checkmark on a piece of paper.[5]
    - If you have fewer than four checkmarks, take a short break (3–5 minutes), then go to step 1.
    - After four pomodoros, take a longer break (15–30 minutes), reset your checkmark count to zero, then go to step 1.

    -- Wikipedia https://en.wikipedia.org/wiki/Pomodoro_Technique

'''


class ClockPanel(QLCDNumber):
    def __init__(self, digits):
        super(ClockPanel, self).__init__()
        self.setDigitCount(digits)

    def update_display(self, background, foreground, display_string):
        self.display(display_string)
        style_string = 'QLCDNumber { background-color : ' + background + '; color : ' + foreground + '; }'
        self.setStyleSheet(style_string)
        self.setSegmentStyle(QLCDNumber.Flat)


class Pomodoro(QWidget):
    def __init__(self, parent):
        super(Pomodoro, self).__init__(parent)

        # interface objects
        self.lcd = ClockPanel(digits=5)
        self.lcd.setFixedHeight(75)
        self.tally = ClockPanel(digits=2)
        self.ledit_pomo_length = QLineEdit('25')
        self.ledit_short_break = QLineEdit('5')
        self.ledit_long_break = QLineEdit('30')
        for ledit in [self.ledit_pomo_length, self.ledit_short_break, self.ledit_long_break]:
            ledit.setFixedWidth(25)
            ledit.setMaxLength(3)
        label_pomo_length = QLabel('Pomodoro (minutes)')
        label_short_break = QLabel('Short Break (minutes)')
        label_long_break = QLabel('Long Break (minutes)')
        layout_grid = QGridLayout()
        layout_grid.setSpacing(1)
        layout_hbox = QHBoxLayout()
        layout_vbox = QVBoxLayout()

        # variables
        self.total = 0
        self.running_flag = 0  # 1 means the timer is running
        self.mode = 0          # 0 = pomodoro, 1 = short break, 2 = long break
        self.colors = ['red', 'green', 'blue']
        self.current_time = timedelta(minutes=0)

        # layout
        # input grid layout & hbox for input row
        layout_grid.addWidget(label_pomo_length, 0, 0)
        layout_grid.addWidget(self.ledit_pomo_length, 0, 1)
        layout_grid.addWidget(label_short_break, 1, 0)
        layout_grid.addWidget(self.ledit_short_break, 1, 1)
        layout_grid.addWidget(label_long_break, 2, 0)
        layout_grid.addWidget(self.ledit_long_break, 2, 1)
        layout_hbox.addLayout(layout_grid)
        layout_hbox.addWidget(self.tally)
        # vbox main layout
        layout_vbox.addLayout(layout_hbox)
        layout_vbox.addWidget(self.lcd)
        self.setLayout(layout_vbox)

    def update_times(self):
        self.times = [timedelta(minutes=int(self.ledit_pomo_length.text())),
                      timedelta(minutes=int(self.ledit_short_break.text())),
                      timedelta(minutes=int(self.ledit_long_break.text()))]

    def started(self):
        self.update_times()
        self.current_time = self.times[self.mode]

        self.running_flag = 1
        self.parent().stop.setDisabled(False)
        self.parent().play.setDisabled(True)
        self.parent().notify = False

    def stopped(self, parent):
        self.update_times()
        if self.mode == 0 and self.current_time >= timedelta(seconds=3):
            self.total = 0
        self.current_time = self.times[self.mode]
        self.running_flag = 0
        self.parent().stop.setDisabled(True)
        self.parent().play.setDisabled(False)


class MainWindow(QMainWindow):
    def __init__(self):
        super(QMainWindow, self).__init__()
        self.pomo = Pomodoro(self)
        self.setCentralWidget(self.pomo)
        # self.sizeHint()
        # self.setFixedSize(300, 150)
        self.setWindowTitle('Pomodoro Timer')
        self.setWindowIcon(QIcon('pomodoro.png'))

        self.style = self.style()

        self.play_icon = QIcon(self.style.standardIcon(QStyle.SP_MediaPlay))
        self.stop_icon = QIcon(self.style.standardIcon(QStyle.SP_MediaStop))
        self.sound_icon = QIcon(self.style.standardIcon(QStyle.SP_MediaVolume))
        self.mute_icon = QIcon(self.style.standardIcon(QStyle.SP_MediaVolumeMuted))
        self.play = QAction(self.play_icon, 'Play', self)
        self.stop = QAction(self.stop_icon, 'Stop', self)
        self.sound = QAction(self.sound_icon, 'Toggle Mute', self)
        self.stop.setDisabled(True)
        self.play.triggered.connect(self.pomo.started)
        self.stop.triggered.connect(self.pomo.stopped)
        self.sound.triggered.connect(self.toggle_sound)

        self.bstick = blinkstick.find_first()
        self.notify = False
        self.muted = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.Time)
        self.timer.start(1000)

        self.toolbar = self.addToolBar('toolbar')
        self.toolbar.addAction(self.play)
        self.toolbar.addAction(self.stop)
        self.toolbar.addAction(self.sound)
        self.toolbar.setMovable(False)
        self.setFixedSize(227, 205)
        self.show()
        self.Time()

    def blink(self):
        red, blue, green = 0, 0, 0
        if self.pomo.colors[self.pomo.mode] == 'red':
            red = 255
        elif self.pomo.colors[self.pomo.mode] == 'blue':
            blue = 255
        elif self.pomo.colors[self.pomo.mode] == 'green':
            green = 255
        while self.notify:
            pass
            self.bstick.pulse(red=red, green=green, blue=blue)

    def display_time(self):
        self.pomo.lcd.update_display(self.pomo.colors[self.pomo.mode], 'white', str(self.pomo.current_time))

    def end_sequence(self, mode_int, total_action):
        if total_action == 'add':
            self.pomo.total += 1
        elif total_action == 'reset':
            self.pomo.total = 0
        self.pomo.mode = mode_int
        self.pomo.stopped(self)
        self.pomo.tally.update_display('red', 'white', str(self.pomo.total))
        if not self.muted:
            QSound.play("ding.wav")
        self.pomo.current_time = self.pomo.times[self.pomo.mode]
        self.notify = True
        blinkthread = Thread(target=self.blink)
        blinkthread.start()
        self.display_time()

    def Time(self):
        self.pomo.tally.update_display('red', 'white', self.pomo.total)

        if self.pomo.running_flag:
            self.pomo.current_time -= timedelta(seconds=1)

        self.display_time()
        if self.pomo.running_flag and self.pomo.mode == 0 and not self.muted:
            QSound.play("tick.wav")

        if self.pomo.running_flag and self.pomo.current_time <= timedelta(seconds=0):
            if self.pomo.total <= 2 and self.pomo.mode == 0:
                self.end_sequence(1, 'add')
            elif self.pomo.total == 3 and self.pomo.mode == 0:
                self.end_sequence(2, 'add')
            elif self.pomo.mode == 2:
                self.end_sequence(0, 'reset')
            else:
                self.end_sequence(0, 'keep')

    def toggle_sound(self):
        if not self.muted:
            self.sound.setIcon(self.mute_icon)
        else:
            self.sound.setIcon(self.sound_icon)
        self.muted = not self.muted


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
