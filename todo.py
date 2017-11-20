#! /usr/bin/env python3.7

###
# File: todo.py
#
# Author: Francesco Tosello
###



from argparse import ArgumentParser

from ansicolor import color

from os.path import expanduser, join as pjoin, isfile, isdir, dirname
from os import makedirs

from re import match, compile as compile_regex

from time import strptime, localtime
import time

import string

import traceback


TODO_FILE = pjoin( expanduser("~"), "Documents", "todo.txt" )
TODO_PATTERN = compile_regex( r"(?:(?P<later>\;\ )?(?:\((?P<priority>[A-Z])\)\ )?(?:\.(?P<due_date>\d{4}\-\d{2}\-\d{2})\ )?(?:(?P<creation_date>\d{4}\-\d{2}\-\d{2})\ )?(?P<todo>[^\&\+\n]*[^\&\+\ ])(?:\ \+(?P<project_name>[^\s\#]+)(?:\#(?P<project_seq>\d+))?)?(?P<tags>(?:\ \&[A-Z\_\d]+)*)?)|^(?P<commented>\;\;).*" )


class TodoTask:
	def __init__(self, line, comment = False):
		line = line.strip()
		if comment or line.startswith(";; "):
			self.later = None
			self.priority = None
			self.due_date = None
			self.creation_date = None
			self.todo = None
			self.project_name = None
			self.project_seq = None
			self.tags = None
			self.commented = True
			self.text = line if line.startswith(";; ") else ";; " + line
		else:
			tm = match(TODO_PATTERN, line)
			if not tm: raise RuntimeError(f"Malformed task: {line}")
			self.later = True if tm.group('later') else False
			self.priority = tm.group('priority')
			self.due_date = strptime(tm.group('due_date'), "%Y-%m-%d") if tm.group('due_date') else None
			self.creation_date = strptime(tm.group('creation_date'), "%Y-%m-%d") if tm.group('creation_date') else None
			self.todo = tm.group('todo').capitalize()
			self.project_name = tm.group('project_name')
			self.project_seq = int(tm.group('project_seq')) if tm.group('project_seq') else 0
			self.tags = [ t.strip() for t in tm.group('tags').split('&')[1:] ] if tm.group('tags') else None
			self.commented = True if tm.group('commented') or self.later else False
			self.text = line

	def __str__(self):
		return self.text

	def __hash__(self):
		return hash( (self.due_date, self.todo.strip().lower() if self.todo else self.text) )

	def __eq__(self, other):
		return self.__hash__() == other.__hash__()

	def colored(self):
		if self.commented: return color(self.text, 'white')

		ts = ""
		if self.priority:
			ts += color("(", 'white') 
			if self.priority == 'A': pcolor = 'red'
			elif self.priority == 'B': pcolor = 'yellow'
			else: pcolor = 'green'
			ts += color(self.priority, pcolor, bold = True) 
			ts += color(") ", 'white')
		if self.due_date:
			ts += color(".", 'white')
			ts += color( str(self.due_date.tm_year) + "-" + str(self.due_date.tm_mon).zfill(2) + "-" + str(self.due_date.tm_mday).zfill(2) + " " , 'magenta', bold = True)
		if self.creation_date:
			ts += color( str(self.creation_date.tm_year) + "-" + str(self.creation_date.tm_mon).zfill(2) + "-" + str(self.creation_date.tm_mday).zfill(2) + " " , 'white')
		ts += color(self.todo, bold = True)
		if self.project_name:
			ts += " " + color("+", 'white') + color(self.project_name, 'blue')
			if self.project_seq: ts += color("#" + str(self.project_seq), 'cyan')
		if self.tags:
			for tag in self.tags:
				ts += " " + color("&", 'white') + ( color(tag, 'red') if tag == "OVERDUE" else color(tag) )

		return ts
		

	def make_todo(todo, due_date = None, priority = None, creation_date = localtime(), project_name = None, project_seq = None, tags = []):
		string = ""
		if "LATER" in tags: string += "; "
		if priority and priority in string.ascii_uppercase: string += "(" + priority + ")" + " "
		if due_date and type(due_date) == time.struct_time:
			string += "." + str(due_date.tm_year) + "-" + str(due_date.tm_mon).zfill(2) + "-" + str(due_date.tm_mday).zfill(2) + " "
		if creation_date and type(creation_date) == time.struct_time:
			string += str(creation_date.tm_year) + "-" + str(creation_date.tm_mon).zfill(2) + "-" + str(creation_date.tm_mday).zfill(2) + " "
		if not todo.strip(): raise RuntimeError( "Empty todo task" )
		string += todo.capitalize()
		if project_name:
			string += " " + f"+{project_name}"
			if project_seq: string += f"#{project_seq}"
		if tags:
			for t in tags:
				t = t.strip()
				if t:
					string += " " + "&" + t.upper()
		return string


def get_tasks(filepath):
	tf = open(filepath, 'r')
	lines = tf.readlines()
	tf.close()

	todos = set()
	for l in lines:
		try:
			todos.add(TodoTask(l))
		except RuntimeError:
			print(color( f"This line will be commented because is not well formatted: {l.strip()}" , 'yellow'))
			todos.add(TodoTask(l, comment = True))

	return todos


def list():
	tasks = get_tasks(TODO_FILE)

	tasks = sorted(tasks, key = lambda x: x.text)

	for t in tasks:
		print( t.colored() )


def add(*tasks):
	todos = get_tasks(TODO_FILE)

	for task in tasks:
		try:

			# if task in todos ... (already present in the set)
			todos.add( TodoTask(task) )
		except RuntimeError:
			print(color("Malformed task.", 'red'))
			continue

	todos = sorted(todos, key = lambda x: x.text)

	tf = open(TODO_FILE, 'w')
	for t in todos:
		tf.write( f"{t}\n" )
	tf.close()

	return True


# Initial checks
if not isfile(TODO_FILE):
	if not isdir(dirname(TODO_FILE)): makedirs(dirname(TODO_FILE))
	open(TODO_FILE,  'a').close() # use 'a' as precaution

# Parse arguments
parser = ArgumentParser(description = "Organize your todos")
parser.add_argument('action', choices = ['add', 'list', 'correct'], help = "Select what you want to do")
parser.add_argument('-t', '--task', action = 'append', dest = 'tasks', help = "The input tasks")
args = parser.parse_args()

# Program start
try:
	if args.action == 'add':
		add(*args.tasks)
	elif args.action == 'list':
		list()
except Exception:
	print(color(traceback.format_exc(), 'red'))
	exit(1)
except KeyboardInterrupt:
	print(color("\nInterrupted!", 'yellow'))
	exit(2)