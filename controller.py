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
_config = lib_config.register('main', {'ADMIN_ID':None, 'SENDER_EMAIL_ADDRESS':None})

guestbook_key = ndb.Key('Guestbook', 'default_guestbook')
member_key = ndb.Key('Member', 'default_member')

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
  token = ndb.StringProperty(required=True)


JINJA_ENVIRONMENT = jinja2.Environment(
  loader = jinja2.FileSystemLoader(os.path.dirname(__file__)),
  extensions = ['jinja2.ext.autoescape'])

class CommonRequest(webapp2.RequestHandler):
  global _config, theme
  bttheme = theme[0]  
  def require_admin(self):
    user = users.get_current_user()
    if user:
      if users.is_current_user_admin():
        return True
      else:
        self.redirect('/error?id=1')
    else:
      self.redirect(users.create_login_url(self.request.uri))

  def is_admin(self):
    user = users.get_current_user()    
    if user and users.is_current_user_admin():
      return True
    else:
      return False

  def get_login_url(self):
    return users.create_login_url(self.request.uri)

class MainPage(CommonRequest):
  def get(self):      
    template = JINJA_ENVIRONMENT.get_template('register.html')
    self.response.out.write(template.render({'is_admin':super(MainPage, self).is_admin(), 'theme': CommonRequest.bttheme, 'login_url': self.get_login_url()}))

class Error(CommonRequest):
  def get(self):
    template = JINJA_ENVIRONMENT.get_template('error.html')
    id = str(self.request.get('id'))
    if id == '1':
      message = '관리자만 접근 할 수 있는 페이지 입니다'
    self.response.out.write(template.render({'message':message.decode("utf8"), 'theme': CommonRequest.bttheme}))

class List(CommonRequest):
  def get(self):    
    super(List, self).require_admin()    
    members = Member.query().order(-Member.created).fetch(1000)
    template = JINJA_ENVIRONMENT.get_template('list.html')
    self.response.out.write(template.render({'members':members, 'is_admin':super(List, self).is_admin(), 'theme': CommonRequest.bttheme, 'login_url': self.get_login_url()}))

class Process(CommonRequest):  
  def post(self):
    import json, sys, random, string    
    from google.appengine.api import mail
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
    member.token = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(15))
    member.put()
    self.response.out.write(json.dumps({'result':True, 'data':None, 'msg':None, 'errorCode':None}))    

def send_mail(host, title, message, admin_email):
  import json, urllib
  from google.appengine.api import mail
  from google.appengine.ext import deferred
  members = Member.query().fetch()
  successed = 0
  failed = 0
  for member in members:
    if not mail.is_email_valid(member.email):
      failed += 1
      continue
    else:          
      try:
        query = urllib.urlencode({'email':member.email, 'token':member.token})
      except UnicodeEncodeError:
        failed += 1
        logging.info('UnicodeEncodeError : ' + member.email)            
        continue
      unsubscribe_link = u'<a href="https://%s/unsubscribe?%s">구독취소</a>' % (host, query)
      mail.send_mail(sender = _config.SENDER_EMAIL_ADDRESS, to = member.email, subject = title, body = message, html = message+'<br /><br />'+unsubscribe_link)
      member.notified = datetime.datetime.now()
      member.put()
      successed += 1
  mail.send_mail(sender = _config.SENDER_EMAIL_ADDRESS, to = admin_email, subject = '이메일 발송을 완료 했습니다.', body = '성공 : %d, 실패 : %d' % (successed, failed))

class Send_process(CommonRequest):  
  global _config
  def post(self):    
    if not super(Send_process, self).is_admin():
       self.redirect(users.create_login_url(self.request.uri))
    import json, urllib
    from google.appengine.api import mail
    from google.appengine.ext import deferred
    title = self.request.get('title')
    message = self.request.get('message')
    send_number = 0
    if title and message:
      deferred.defer(send_mail, self.request.host, title, message, users.get_current_user().email())      
      self.response.out.write(json.dumps({'result':True, 'data':None, 'msg':None, 'errorCode':None}))
    else:
      self.response.out.write(json.dumps({'result':False, 'data':None, 'msg':'parameter quantity is wrong', 'errorCode':1}))

class Unsubscribe(CommonRequest):
  def get(self):
    member = Member.query(Member.email == self.request.get('email'), Member.token == self.request.get('token')).get()
    if(member):
      member.key.delete()
      self.response.out.write('<html><body><script>alert("구독을 취소 했습니다.");history.back()</script></body></html>')      
    else:
      self.response.out.write('<html><body><script>alert("존재하지 않는 계정입니다.");history.back()</script></body></html>')      

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
    super(Migration, self).require_admin()  
    import csv, random, string
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
        member.token = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(15))
        i = i + 1
        future = member.put_async()
        future.get_result()
    self.response.out.write(i)

class Reset(CommonRequest):
  def get(self):
    super(Reset, self).require_admin()  
    members = Member.query().fetch()
    for m in members:
      logging.info(m.key.delete())

app = webapp2.WSGIApplication([
  ('/', MainPage),
  ('/process', Process),
  ('/list', List),
  ('/send_process', Send_process),
  ('/migration', Migration),
  ('/reset', Reset),
  ('/error', Error),
  ('/delete_process', Delete_process),
  ('/unsubscribe', Unsubscribe)
], debug=True)

def main():
  logging.getLogger().setLevel(logging.INFO)
