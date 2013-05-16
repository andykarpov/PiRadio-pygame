#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import codecs
import time
import datetime
import serial
import textwrap
from random import randrange
from fenix.program import Program
from fenix.process import Process 
import pygame
from pygame.locals import *
from fenix.locals import *
from mpd import MPDClient

class Config:

	default_screen_size = (640, 480)
	fps = 30
	full_screen = True
	detect_screen_size = True
	fb_dev = "/dev/fb0"
	serial_dev = ["/dev/ttyAMA0", "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/tty.usbserial-A50059JB"]
	serial_speed = 9600
	menu_size = 25

	main_bg_color = (0, 0, 102)
	clock_color = (224, 224, 224)
	title_color = (255, 255, 255)
	station_color = (128, 128, 128)
	song_color = (255, 255, 255)

	menu_bg_color = (0, 0, 102)
	menu_color = (255, 255, 255)
	menu_color_active = (0, 255, 255)

	menu_font = "gfx/zxsp____.ttf"
	menu_font_bold = "gfx/zxspb___.ttf"
	playlist = "data/radio.m3u"
	state = "data/state.txt"
	save_timeout = 500
	mpd_host = "localhost"
	mpd_port = 6600
	mpd_password = None

class Encoder:

	serial = None
	serial_connected = False
	encoder = 0
	min_value = 0
	max_value = 0

	def __init__(self, encoder = 0, min_value = 0, max_value = 0):
		self.encoder = encoder
		self.min_value = min_value
		self.max_value = max_value
		self.try_serial()

	def try_serial(self):
		for serial_dev in Config.serial_dev:
			if (self.serial_connected == False):
				try:
					self.serial = serial.Serial(serial_dev, Config.serial_speed)
					self.serial.write('SET_ENC:' + str(self.encoder * 4) + "\n")
					self.serial_connected = True
				except Exception as e:
					self.serial_connected = False

	def try_write(self, data):
		try:
			self.serial.write(data + "\n")
			return True
		except Exception as e:
			self.serial_connected = False
			self.try_serial()
			return False

	def try_read(self):
		change_scene_request = False
		try:
			if (self.serial_connected and self.serial.inWaiting()):

				ln = self.serial.readline() 
				ln = ln.strip();
				if (ln == "up" or ln == "down" or ln == "left" or ln == "right" or ln == "ok" or ln == "menu" or ln == "play"):
					if (ln == "ok" or ln == "menu" or ln =="play"):
						change_scene_request = True
					elif (ln == "up"):
						self.encoder = self.encoder - 1
						if (self.encoder < self.min_value):
							self.encoder = self.min_value
					elif (ln == "down"):
						self.encoder = self.encoder + 1
						if (self.encoder > self.max_value):
							self.encoder = self.max_value
					
											
				else:
					if (ln != ""):
						reading = ln.strip().split(':')
					
						if (int(reading[1]) > 0):
							change_scene_request = True
						else:
							self.encoder = int(round(int(reading[0])/4))
							need_trim = False
							if (self.encoder < self.min_value):
								self.encoder = self.min_value
								need_trim = True
							if (self.encoder > self.max_value):
								self.encoder = self.max_value
								need_trim = True
							if (need_trim):
								self.try_write('SET_ENC:' + str(self.encoder*4));
			return change_scene_request
		except Exception as e:
			return None

	def set_enc(self, value):
		return self.try_write('SET_ENC:' + str(value*4))

	def led_red(self, value):
		if (value == True):
			str = 'LED_RED:1'
		else:
			str = 'LED_RED:0'
		return self.try_write(str)

	def led_green(self, value):
		if (value == True):
			str = 'LED_GREEN:1'
		else:
			str = 'LED_GREEN:0'
		return self.try_write(str)

class Game(Process):

	screen_size = Config.default_screen_size
	fps = Config.fps
	full_screen = Config.full_screen
	playlist = None
	mpd = None
	state = None
	active_song = 0
	last_active_song = 0
	last_changed = 0
	window_title = "Python Radio for Raspberry Pi"
	encoder = None

	""" The main game process sets up the scene and checks for
	the escape key being pressed (for quitting)
	"""
	def begin(self):

		# Set fb device for Raspberry pi
		#os.environ["SDL_FBDEV"] = Config.fb_dev

		"Ininitializes a new pygame screen using the framebuffer"
		# Based on "Python GUI in Linux frame buffer"
		# http://www.karoltomala.com/blog/?p=679
		disp_no = os.getenv("DISPLAY")
		if disp_no:
		    print "I'm running under X display = {0}".format(disp_no)

		# Check which frame buffer drivers are available
		# Start with fbcon since directfb hangs with composite output
		drivers = ['fbcon', 'directfb', 'svgalib']
		found = False
		for driver in drivers:
			# Make sure that SDL_VIDEODRIVER is set
			if not os.getenv('SDL_VIDEODRIVER'):
				os.putenv('SDL_VIDEODRIVER', driver)
			try:
				pygame.display.init()
			except pygame.error:
				print 'Driver: {0} failed.'.format(driver)
				continue
			found = True
			break

		if not found:
			raise Exception('No suitable video driver found!')

		if (Config.detect_screen_size):
			self.screen_size = (pygame.display.Info().current_w, pygame.display.Info().current_h)

		# Set the resolution and the frames per second
		Program.set_mode(self.screen_size, self.full_screen, False)
		Program.set_fps(self.fps)
		#Program.set_title(self.window_title)

		# set mouse invisible
		pygame.mouse.set_visible(False)

		# load playlist
		self.playlist = Playlist()
		self.playlist.load(Config.playlist)

		# init mpd
		self.mpd = MPDClient()
		self.mpd.connect(Config.mpd_host, Config.mpd_port)
		if (Config.mpd_password is not None):
			self.mpd.password(Config.mpd_password)		

		# collect mpd playlist
		self.mpd.stop()
		self.mpd.clear()
		for item in self.playlist.list:
			self.mpd.add(item.url)
		# get active song from saved state
		self.state = State()
		self.active_song = self.state.load()
		self.last_active_song = self.active_song

		# init serial encoder instance
		self.encoder = Encoder(self.active_song, 0, len(self.playlist.list)-1)

		# play
		self.mpd.play(self.active_song)

		# run scene
		scene = Main(self);

		while True:
			# This is the main loop

			# Simple input check
			if (Program.key(K_ESCAPE)):
				Program.exit()

			change_scene_request = self.encoder.try_read()

			if (self.millis() - self.last_changed >= Config.save_timeout and self.last_active_song != self.active_song):
				self.last_active_song = self.active_song
				self.mpd.play(self.active_song)
				self.state.save(self.active_song)

			if (Program.key_released(K_SPACE) or Program.key_released(K_RETURN) or change_scene_request == True):
				change_scene_request = False
				if (isinstance(scene, Menu)):
					scene.signal(S_KILL, True)
					scene = Main(self)
				elif (isinstance(scene, Main)):
					scene.signal(S_KILL, True)
					scene = Menu(self)

			# The yield statement signifies that this object is finished for the
			# current frame, on the next frame the loop will resume here until it
			# hits the yield statement again. All objects are designed to act this way.
			yield

	def calculate_page(self, dir):
		self.last_changed = self.millis()
		if (dir < 0):
			self.active_song += dir
			if (self.active_song <0): 
				self.active_song = 0

		if (dir > 0):
			self.active_song += dir
			if (self.active_song > len(self.playlist.list) - 1):
				self.active_song = len(self.playlist.list) - 1

	def millis(self):
		return int(round(time.time() * 1000))


class Main(Process):

	game = None
	last_current_song = 0
	current_song = ''

	def calculate_page(self, dir):
		self.current_song = ''
		self.game.calculate_page(dir)

	def get_x(self):
		return 10

	def get_y(self, pos):
		return (self.game.screen_size[1]/2) + pos * (self.game.screen_size[1]/8) + 10

	def begin(self, game):

		self.game = game

		self.game.encoder.led_red(True);
		self.game.encoder.led_green(True);

		Bg(game, Config.main_bg_color);

		# Bars(self)
		Clock(self)

		font = Program.load_fnt(Config.menu_font, self.game.screen_size[1]/18)
		font2 = Program.load_fnt(Config.menu_font, self.game.screen_size[1]/20)
		font3 = Program.load_fnt(Config.menu_font, self.game.screen_size[1]/24)

		station_name = Program.write(font, self.get_x(), self.get_y(0), 0, '')
		station_name.colour = Config.title_color

		playlist_pos = Program.write(font2, self.get_x(), self.get_y(1), 0, '')
		playlist_pos.colour = Config.station_color

		artist_name1 = Program.write(font3, self.get_x(), self.get_y(2), 0, '')
		artist_name1.colour = Config.song_color
		artist_name2 = Program.write(font3, self.get_x(), self.get_y(2.5), 0, '')
		artist_name2.colour = Config.song_color

		scroll_width = 0
		scroll_count = 0
		scroll_total_count = 0

		while True:

			# fetch current song from mpd every 500ms
			if (self.game.millis() - self.last_current_song > 500):
				current_song = self.game.mpd.currentsong();
				#print current_song
				if 'title' in current_song:
					title = current_song['title'].strip()
					try:
						title = title.decode('utf8')
					except Exception as e:
						pass

					if (title != self.current_song):
						scroll_width = 0
						scroll_count = 0
						scroll_total_count = 0
						self.current_song = title.upper()
						for l in self.current_song:
							scroll_width += font3.size(l)[0]
							scroll_total_count = scroll_total_count+1
							if (scroll_width <= self.game.screen_size[0] - self.get_x()):
								scroll_count = scroll_count+1
				else:
					self.current_song = ''
					scroll_width = 0
					scroll_count = 0
					scroll_total_count = 0
				self.last_current_song = self.game.millis()

				#if ('pos' in current_song and int(current_song['pos']) != self.game.active_song):
				#	self.game.active_song = int(current_song['pos'])
				#	self.game.last_active_song = int(current_song['pos'])


			# pring station, pos and song title
			station = self.game.playlist.list[self.game.active_song]
			station_name.text = station.name.upper()
			playlist_pos.text = u'STATION ' + str(self.game.active_song+1) + u' / ' + str(len(self.game.playlist.list))

			if (scroll_total_count > scroll_count):
				part = textwrap.wrap(self.current_song, scroll_count)
				if(len(part)>=2):
					artist_name1.text = part[0]
					artist_name2.text = part[1]
				else:
					artist_name1.text = ''
					artist_name2.text = self.current_song
			else:
				artist_name1.text = ''
				artist_name2.text = self.current_song

			if (self.game.encoder.serial_connected == True and self.game.encoder.encoder != self.game.active_song):
				self.calculate_page(self.game.encoder.encoder - self.game.active_song)

			if (Program.key_released(K_UP)):
				self.calculate_page(-1);

			if (Program.key_released(K_DOWN)):
				self.calculate_page(1);

			yield

class Clock(Process):

	main = None
	last_blinked = 0
	blinked = False

	def begin(self, main):

		self.main = main

		font = Program.load_fnt(Config.menu_font_bold, self.main.game.screen_size[1]/5)
		clock = Program.write(font, self.main.game.screen_size[0]/2, self.main.game.screen_size[1]/4, 4, '')
		clock.colour = Config.clock_color

		while True:

			dt = datetime.datetime.now()
			hours = dt.strftime('%H')
			minutes = dt.strftime('%M')
			if (self.main.game.millis() - self.last_blinked >= 500):
				self.last_blinked = self.main.game.millis()
				self.blinked = not self.blinked
			if (self.blinked):
				blink = ':'
			else:
				blink = ' '

			clock.text = hours + blink + minutes

			yield

class Bg(Process):

	def begin(self, game, color):

		self.x = game.screen_size[0]/2
		self.y = game.screen_size[1]/2
		self.size = 100
		self.graph = Program.new_map(game.screen_size[0], game.screen_size[1])
		Program.map_clear(self.graph, color)

		while True:

			yield

class Bars(Process):

	main = None

	bars_count = 10

	def begin(self, main):

		self.main = main

		self.values = [10,20,30,40,50,60,70,80,90,100]
		self.prev_values = [0,0,0,0,0,0,0,0,0,0]

		for i in range(0, self.bars_count):
			Bar(self, i)

		while True:

			# todo: make a real fftw transformations here from the mpd fifo data
			# dummy
			#for i in range(0, self.bars_count):
			#	self.values[i] = randrange(0,100)

			yield

class Bar(Process):

	bars = None

	def begin(self, bars, idx):

		self.bars = bars

		bar_width = round((self.bars.main.game.screen_size[0] / self.bars.bars_count))
		bar_height = round(self.bars.main.game.screen_size[1] / 2)

		self.x = ((bar_width) * idx) + round(bar_width/2)
		self.size = 100

		while True:

			if (self.bars.values[idx] != self.bars.prev_values[idx]):
				self.bars.prev_values[idx] = self.bars.values[idx]
				self.y = bar_height - round(((bar_height/2) * self.bars.values[idx]) / 100)
				self.graph = Program.new_map(bar_width-4, round(bar_height * self.bars.values[idx] / 100) )
				cl = self.bars.values[idx] * 255 / 100
				self.alpha = cl
				color = (0, 0, 255)
				Program.map_clear(self.graph, color)

			yield

class Menu(Process):

	menu_size = Config.menu_size
	page = 0
	game = None
	state = None
	item_color = Config.menu_color
	selected_item_color = Config.menu_color_active

	def calculate_page(self, dir):
		self.game.calculate_page(dir);
		self.page = self.game.active_song//self.menu_size

	def begin(self, game):

		# loading resources
		self.menu_font = Program.load_fnt(Config.menu_font, game.screen_size[1]/self.menu_size)
		self.game = game
		self.state = game.state
		self.last_active_menu = self.game.active_song
		self.calculate_page(0)

		self.game.encoder.led_red(False);
		self.game.encoder.led_green(True);

		Bg(game, Config.menu_bg_color)

		# creating menu items
		for i in range(0, len(self.game.playlist.list)):
			item = game.playlist.list[i]
			MenuItem(self, i, item.name.upper())

		while True:

			if (self.game.encoder.serial_connected == True and self.game.encoder.encoder != self.game.active_song):
				self.calculate_page(self.game.encoder.encoder - self.game.active_song)

			if (Program.key_released(K_UP)):
				self.calculate_page(-1);

			if (Program.key_released(K_DOWN)):
				self.calculate_page(1);

			if (Program.key_released(K_LEFT)):
				self.calculate_page(-self.menu_size);

			if (Program.key_released(K_RIGHT)):
				self.calculate_page(self.menu_size);

			yield


class MenuItem(Process):

	idx = 0
	menu = None

	def get_x(self):
		return 10

	def get_y(self):
		return self.idx*(self.menu.game.screen_size[1])/self.menu.menu_size - (self.menu.page * self.menu.game.screen_size[1])

	def get_name(self):

		display_num = str(self.idx + 1).zfill(2)

		if (self.menu.game.active_song == self.idx):
			display_space = '] '
			display_left = '['
		else:
			display_space = '  '
			display_left = ' '

		return display_left + display_num + display_space + self.name

	def get_color(self):
		if (self.menu.game.active_song == self.idx):
			color = self.menu.selected_item_color
		else:
			color = self.menu.item_color
		return color

	def begin(self, menu, idx, name):

		self.idx = idx
		self.menu = menu
		self.name = name

		item = Program.write(menu.menu_font, self.get_x(), self.get_y(), 0, '')

		while True:

			item.colour = self.get_color()
			item.text   = self.get_name()
			item.y = self.get_y()
				
			yield
			
class State:

	def load(self):
		try:
			result = 0
			fsrc = codecs.open(Config.state, mode="r", encoding="utf-8")
			ln = fsrc.readline().strip()
			if (ln != ""):
				result = int(ln)
			fsrc.close()
			return result
		except Exception as e:
			print "Unable to load state:", e
			return 0

	def save(self, active_menu):
		try:
			fsrc = codecs.open(Config.state, mode="w", encoding="utf-8")
			fsrc.write(str(active_menu))
			fsrc.close()
		except Exception as e:
			print "Unable to store state:", e


class PlaylistItem:

	def __init__(self):
		self.name = None
		self.url = None
		self.payload = []

class Playlist:

	list = []

	def __init__(self):
		self.list = []

	def load(self, filename):
		try:
			fsrc = codecs.open(filename, mode="r", encoding="utf-8")
			self.parse(fsrc)
			fsrc.close()
		except Exception as e:
			print "Error while loading playlist: ", e

	def parse(self, infile):
		ln = None
		self.list = []

		while (ln != "" and ln != u"#EXTM3U\n"):
			ln = infile.readline()

 		ln = infile.readline()
		while (ln != ""):
			while (ln != "" and ln.find(u"#EXTINF") == -1):
				ln = infile.readline()
			match = re.search(ur"#EXTINF:.*,(.*)", ln)
 			name = match.group(1)
			nitem = PlaylistItem()
			nitem.name = name
			ln = infile.readline()
			while (ln != "" and ln.find(u"#EXTINF") == -1):
				nitem.payload.append(ln)
				ln = infile.readline()
			nitem.url = nitem.payload[-1].strip()
			self.list.append(nitem)


if __name__ == '__main__':
	# To start the game we create the main Game process. The first time
	# a process is created pygame-fenix will invisibly initialise
	# itself. There is no need to specifically tell pygame-fenix to start
	# dealing wih processes.
	# This method of creating objects and having them immediately enter
	# into existance in a real way makes writing games extremely simple.
	# Write the game and not the engine.
	Game()
