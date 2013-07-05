#!/usr/bin/env python
# -*- coding:utf-8 -*-

import cgi
import datetime
import webapp2
import jinja2
import os
import logging
import random
from google.appengine.ext import ndb
from google.appengine.api import users

from google.appengine.api import lib_config
_config = lib_config.register('main', {'ADMIN_ID':None})

guestbook_key = ndb.Key('Guestbook', 'default_guestbook')
member_key = ndb.Key('Member', 'default_member')
admin_id = 'egoing@gmail.com'

theme = [
 'netdna.bootstrapcdn.com/twitter-bootstrap/2.3.2/css/bootstrap-combined.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/amelia/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/cerulean/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/cosmo/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/cyborg/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/flatly/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/journal/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/readable/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/simplex/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/slate/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/spacelab/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/spruce/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/superhero/bootstrap.min.css'
,'netdna.bootstrapcdn.com/bootswatch/2.3.2/united/bootstrap.min.css']

class Greeting(ndb.Model):
  author = ndb.UserProperty()
  content = ndb.TextProperty()
  date = ndb.DateTimeProperty(auto_now_add=True)

class Member(ndb.Model):
  nickname = ndb.StringProperty(required=False)
  email = ndb.StringProperty(required=True)
  comment = ndb.TextProperty(required=False)    
  region = ndb.TextProperty(required=False)    
  created = ndb.DateTimeProperty(auto_now_add=True)
  notified = ndb.DateTimeProperty(auto_now_add=True)
  twitter = ndb.StringProperty(required=False)
  phone = ndb.StringProperty(required=False)


JINJA_ENVIRONMENT = jinja2.Environment(
  loader = jinja2.FileSystemLoader(os.path.dirname(__file__)),
  extensions = ['jinja2.ext.autoescape'])

class CommonRequest(webapp2.RequestHandler):
  global _config, theme
  bttheme = theme[0]  
  def is_admin(self):
    user = users.get_current_user()    
    if user and user.email() == _config.ADMIN_ID: 
      return True
    else:
      return False
  def get_login_url(self):
    return users.create_login_url(self.request.uri)

class MainPage(CommonRequest):
  def get(self):      
    template = JINJA_ENVIRONMENT.get_template('register.html')
    self.response.out.write(template.render({'is_admin':super(MainPage, self).is_admin(), 'theme': CommonRequest.bttheme, 'login_url': self.get_login_url()}))

class List(CommonRequest):
  def get(self):    
    if not super(List, self).is_admin():
       self.redirect(users.create_login_url(self.request.uri))
    members = Member.query().order(-Member.created).fetch(1000)
    template = JINJA_ENVIRONMENT.get_template('list.html')
    self.response.out.write(template.render({'members':members, 'is_admin':super(List, self).is_admin(), 'theme': CommonRequest.bttheme, 'login_url': self.get_login_url()}))

class Process(CommonRequest):  
  def post(self):
    import json, sys    
    from google.appengine.api import mail
    logging.info(mail.is_email_valid(self.request.get('email')))
    if not mail.is_email_valid(self.request.get('email')):
      self.response.out.write(json.dumps({'result':False, 'data':None, 'msg':'이메일 주소를 올바르게 입력해주세요', 'errorCode':1}))    
      return
    member = Member(parent=member_key)
    member.nickname = self.request.get('nickname')
    member.email = self.request.get('email')
    member.region = self.request.get('region')
    member.comment = self.request.get('comment')
    member.twitter = self.request.get('twitter')
    member.phone = self.request.get('phone')    
    member.put()
    self.response.out.write(json.dumps({'result':True, 'data':None, 'msg':None, 'errorCode':None}))    

class Guestbook(CommonRequest):
  def post(self):
    greeting = Greeting(parent=guestbook_key)    

    if users.get_current_user():
      greeting.author = users.get_current_user()

    greeting.content = self.request.get('content')
    greeting.put()
    self.redirect('/')

class Send_process(CommonRequest):  
  global admin_id
  def post(self):
    if not super(Send_process, self).is_admin():
       self.redirect(users.create_login_url(self.request.uri))
    import json
    from google.appengine.api import mail

    title = self.request.get('title')
    message = self.request.get('message')
    if title and message:
      members = Member.query().fetch()
      sender_list = []
      for member in members:
        if not mail.is_email_valid(member.email):
          continue
        else:    
          sender_list.append(member.email)
          member.notified = datetime.datetime.now()
          member.put()
      title = self.request.get('title')          
      message = self.request.get('message')
      mail.send_mail(sender = 'egoing@gmail.com', to = admin_id, bcc = ','.join(sender_list), subject = title, body = message)
      self.response.out.write(json.dumps({'result':True, 'data':None, 'msg':None, 'errorCode':None}))
    else:      
      self.response.out.write(json.dumps({'result':False, 'data':None, 'msg':'parameter quantity is wrong', 'errorCode':1}))

class Delete_process(CommonRequest):
  def post(self):
    import json    
    if not super(Delete_process, self).is_admin():
      self.response.out.write(json.dumps({'result':False, 'data':None, 'msg':'인증이 필요합니다', 'errorCode':1}))
      return
    id = int(self.request.get('id'))
    
    member = Member.get_by_id(id, parent=member_key)
    logging.info(dir(member))
    member.key.delete()
    self.response.out.write(json.dumps({'result':True, 'data':None, 'msg':None, 'errorCode':None}))

class Migration(CommonRequest):
  def get(self):
    if not super(Migration, self).is_admin():
       self.redirect(users.create_login_url(self.request.uri))
    import csv
    with open('jacsim.csv', 'rb') as csvfile:
      c = csv.reader(csvfile)
      i = 0
      for row in c:
        created = row[0]
        nickname = row[1]
        email = row[2]
        comment = row[3]
        region = row[4]
        member = Member(parent = member_key)
        member.nickname = nickname
        member.email = email
        member.comment = comment
        i = i + 1
        member.put()
    self.response.out.write(i)

class Reset(CommonRequest):
  def get(self):
    if not super(Reset, self).is_admin():
       self.redirect(users.create_login_url(self.request.uri))
    members = Member.query().fetch()
    for m in members:
      logging.info(m)
      logging.info(m.key.delete())

app = webapp2.WSGIApplication([
  ('/', MainPage),
  ('/sign', Guestbook),
  ('/process', Process),
  ('/list', List),
  ('/send_process', Send_process),
  ('/migration', Migration),
  ('/reset', Reset),
  ('/delete_process', Delete_process)
], debug=True)

def main():
  logging.getLogger().setLevel(logging.INFO)
  logging.info(admin_id)