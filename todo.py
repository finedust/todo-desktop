#! /usr/bin/env python3.6

###
# File: todo.py
#
# Author: Francesco Tosello
###



from argparse import ArgumentParser

from os.path import expanduser, join as pjoin, isfile, isdir, dirname
from os import makedirs

from re import match, compile as compile_regex

from datetime import datetime, timedelta

import string

import traceback


TODO_FILE = pjoin( expanduser("~"), "Documents", "todo.txt" )
TODO_PATTERN = compile_regex( r"(?:(?P<later>\;\ )?(?:\((?P<priority>[A-Z])\)\ )?(?:\.(?P<due_date>\d{4}\-\d{2}\-\d{2})\ )?(?:(?P<creation_date>\d{4}\-\d{2}\-\d{2})\ )?(?P<todo>[^\:\+\n]*[^\:\+\ ])(?:\ \+(?P<project_name>[^\s\#]+)(?:\#(?P<project_seq>\d+))?)?(?P<tags>(?:\ \:[A-Z\_\d]+)*)?)|^(?P<comment>\;\;).*" )
URGENT_TIME = timedelta(days = 7)


class TodoTask:
	def __init__(self, line, comment = False, prioritize = True):
		line = line.strip()
		if comment or line.startswith(";; "):
			self.later = None
			self.priority = None
			self.due_date = None
			self.creation_date = None
			self.todo = None
			self.project_name = None
			self.project_seq = None
			self.tags = set()
			self.comment = True
			self.text = line if line.startswith(";; ") else ";; " + line
		else:
			tm = match(TODO_PATTERN, line)
			if not tm: raise RuntimeError(f"Malformed task: {line}")
			
			self.tags = set([ t.strip() for t in tm.group('tags').split(':')[1:] if t ] if tm.group('tags') else [])
			
			self.due_date = datetime.strptime(tm.group('due_date'), "%Y-%m-%d") if tm.group('due_date') else None
			if self.due_date and self.due_date < datetime.now(): self.tags.add("OVERDUE")

			self.priority = tm.group('priority')
			if "OVERDUE" in self.tags:
				self.priority = "A"
			elif self.due_date and self.due_date - datetime.now() < URGENT_TIME and self.priority != "A" and self.priority != "B":
				self.priority = "C"
			
			self.creation_date = datetime.strptime(tm.group('creation_date'), "%Y-%m-%d") if tm.group('creation_date') else datetime.now()
			
			self.todo = tm.group('todo').capitalize()
			
			self.project_name = tm.group('project_name')
			self.project_seq = int(tm.group('project_seq')) if tm.group('project_seq') else 0
			
			if tm.group('later'):
				self.later = True
				self.tags.add("LATER")
			elif self.tags.intersection({"LATER", "WAITING"}):
				self.later = True
			else:
				self.later = False
			
			self.comment = False
			
			self.text = make_todo(self.todo, self.due_date, self.priority, self.creation_date, self.project_name, self.project_seq, self.tags)

	def __str__(self):
		return self.text

	def __hash__(self):
		return hash( (self.due_date, self.todo.strip().lower() if self.todo else self.text) )

	def __eq__(self, other):
		return self.__hash__() == other.__hash__()

	def colored(self):
		if self.comment or self.later: return color(self.text, 'white')

		ts = ""
		if self.priority:
			ts += color("(", 'white') 
			if self.priority == 'A': pcolor = 'red'
			elif self.priority == 'B' or self.priority == 'C': pcolor = 'yellow'
			else: pcolor = 'green'
			ts += color(self.priority, pcolor, bold = True) 
			ts += color(") ", 'white')
		if self.due_date:
			ts += color(".", 'white')
			ts += color(self.due_date.strftime("%y-%m-%d "), 'magenta', bold = True)
		#if self.creation_date:
		ts += color(self.creation_date.strftime("%y-%m-%d "), 'white')
		ts += color(self.todo, bold = True)
		if self.project_name:
			ts += " " + color("+", 'white') + color(self.project_name, 'blue')
			if self.project_seq: ts += color("#" + str(self.project_seq), 'cyan')
		if self.tags:
			for tag in self.tags:
				ts += " " + color(":", 'white') + ( color(tag, 'red') if tag == "OVERDUE" else color(tag, 'green') )

		return ts
		

def make_todo(todo, due_date = None, priority = None, creation_date = datetime.now(), project_name = None, project_seq = None, tags = set()):
	todo_string = ""
	if tags.intersection({"LATER", "WAITING"}): todo_string += "; "
	if priority and priority in string.ascii_uppercase: todo_string += "(" + priority + ")" + " "
	if due_date and type(due_date) == datetime:
		todo_string += due_date.strftime(".%y-%m-%d ")
	if creation_date and type(creation_date) == datetime:
		todo_string += creation_date.strftime("%y-%m-%d ")
	if not todo.strip(): raise RuntimeError( "Empty todo task" )
	todo_string += todo.capitalize()
	if project_name:
		todo_string += " " + f"+{project_name}"
		if project_seq: todo_string += f"#{project_seq}"
	if tags:
		for t in tags:
			t = t.strip()
			if t:
				todo_string += " :" + t.upper()
	return todo_string


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


def list(projects = [], tags = []):
	tasks = get_tasks(args.file)

	if tags:
		for task in set(tasks):
			if len( task.tags.intersection(set(tags)) ) <= 0: tasks.discard(task)

	tasks = sorted(tasks, key = lambda x: x.text)

	for t in tasks:
		print( t.colored() )


def add(*tasks):
	todos = get_tasks(args.file)

	for task in tasks:
		try:

			# if task in todos ... (already present in the set)
			todos.add( TodoTask(task) )
		except RuntimeError:
			print(color("Malformed task.", 'red'))
			continue

	todos = sorted(todos, key = lambda x: x.text)

	tf = open(args.file, 'w')
	for t in todos:
		tf.write( f"{t}\n" )
	tf.close()

	return True


# Parse arguments
parser = ArgumentParser(description = "Organize your todos")
parser.add_argument('action', choices = ['add', 'list', 'correct'], help = "Select what you want to do")
parser.add_argument('-t', '--task', action = 'append', dest = 'tasks', help = "The input tasks")
parser.add_argument('-f', '--file', default = TODO_FILE, help = "Todo.txt file to use")
tasks_filters = parser.add_argument_group("Tasks filters")
tasks_filters.add_argument('--tag', dest = 'tags', action = 'append', help = "Filter only specific tags (not case sensitive)")
args = parser.parse_args()

# Initial checks
if not isfile(args.file):
	if not isdir(dirname(args.file)): makedirs(dirname(args.file))
	open(args.file,  'a').close() # use 'a' as precaution
print( f"Selected todo.txt file: {args.file}" )

# Program start
try:
	if args.action == 'add':
		add(*args.tasks)
	elif args.action == 'list':
		list(tags = args.tags)
except Exception:
	print(color(traceback.format_exc(), 'red'))
	exit(1)
except KeyboardInterrupt:
	print(color("\nInterrupted!", 'yellow'))
	exit(2)