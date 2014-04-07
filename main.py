# coding:UTF-8

import os
import tornado.web
import tornado.ioloop
import tornado.httpserver
import tornado.options
import httplib,urllib
import json
import dnspod
import base64

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
  def __init__(self):
    handlers = [
    (r"/",IndexHandler),
    (r"/login",LoginHandler),
    (r"/logout",LogoutHandler),
    (r"/domains/([0-9]+)/",ShowDomainHandler),
    (r"/domains/([0-9]+)/record/(\w+)",RecordHandler),
    (r"/domain/(\w+)",DomainHandler),
    ]
    settings = dict(
      cookie_secret="61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
      login_url="/login",
      site_name = "Fake DNSPOD",
      site_url = "http://192.168.56.5/",
      template_path = os.path.join(os.path.dirname(__file__),"templates"),
      static_path = os.path.join(os.path.dirname(__file__),"static"),
      )
    tornado.web.Application.__init__(self, handlers, **settings)

class BaseHandler(tornado.web.RequestHandler):
  def get_current_user(self):
    return self.get_secure_cookie("uemail")

class LogoutHandler(BaseHandler):
  def get(self):
    self.set_secure_cookie("uemail","",expires_days=None)
    self.set_secure_cookie("upwd","",expires_days=None)
    self.redirect("/login")  

class LoginHandler(BaseHandler):
  def get(self):
    if self.current_user:
      self.redirect("/")
    else:
      self.render("login.html",error=0)
  def post(self):
    raw_email = self.get_argument("uemail",default="",strip=True)
    raw_pwd = self.get_argument("upwd",default="",strip=True)
    if raw_email and raw_pwd:
      operation = dnspod.UserDetail(raw_email,raw_pwd)
      response = operation.request()
      if response["status"]["code"] == "1":
        self.set_secure_cookie("uemail",raw_email,expires_days=None)
        self.set_secure_cookie("upwd",raw_pwd,expires_days=None)
        self.redirect("/")
      else:
        self.render("login.html",error=1)

class IndexHandler(BaseHandler):
  @tornado.web.authenticated
  def get(self):
    uemail = self.current_user
    upwd = self.get_secure_cookie("upwd")
    operation = dnspod.DomainList(uemail,upwd)
    response = operation.request()
    print(response)
    self.render("index.html", uemail=uemail, domains = response["domains"])

class DomainHandler(BaseHandler):
  def post(self,oper):
    uemail = self.current_user
    upwd = self.get_secure_cookie("upwd")
    oper_list = ["add", "delete"]
    response = {"status":{"code":"-1"}}

    if uemail and upwd and oper in oper_list :
      if oper == "add":
        domain = self.get_argument("domain",default="",strip=True)
        if domain:
          operation = dnspod.DomainCreate(uemail,upwd,domain)
          response = operation.request()

      elif oper == "delete":
        domain_id_list = self.get_arguments("domain_id_list[]")
        for domain_id in domain_id_list:
          operation = dnspod.DomainRemove( uemail, upwd, domain_id )
          response = operation.request()

    self.write(json.dumps(response))

class ShowDomainHandler(BaseHandler):
  @tornado.web.authenticated
  def get(self,num):
    uemail = self.current_user
    upwd = self.get_secure_cookie("upwd")
    domain_id = num

    if domain_id:
      operation = dnspod.RecordList(uemail,upwd,domain_id)
      response = operation.request()
      print(response)
      res = response["status"]["code"];
      if res=="1":
        #生成导出文件的内容
        content = u"主机|类型|线路|记录值|MX优先级|TTL\r\n"
        for record in response["records"]:
            content = content + record["name"] + u" " + record["type"] + u" " + record["line"]
            content = content + u" " + record["value"] + u" " + record["mx"] + u" " + record["ttl"] +"\r\n"
        self.render("showdomain.html", res=int(res), uemail=uemail, domain_name=response["domain"]["name"], records=response["records"], content=base64.b64encode(content.encode("UTF-8")))
      else:
        self.redirect("/")

class RecordHandler(BaseHandler):
  def post(self,num,oper):
    uemail = self.current_user
    upwd = self.get_secure_cookie("upwd")
    domain_id = num
    oper_list = ["add", "delete", "enable", "disable", "modify", "import"]
    response = {"status":{"code":"-1"}}

    if uemail and upwd and domain_id and oper in oper_list :
      if oper == "add" :
        operation = dnspod.RecordCreate(uemail, upwd, domain_id,
                                      self.get_argument("sub_domain").encode("UTF-8"),
                                      self.get_argument("record_type").encode("UTF-8"),
                                      self.get_argument("line").encode("UTF-8"),
                                      self.get_argument("value").encode("UTF-8"),
                                      self.get_argument("ttl").encode("UTF-8"),
                                      self.get_argument("mx").encode("UTF-8"),
                                      )
        response = operation.request()

      elif oper == "delete":
        rec_id_list = self.get_arguments("rec_id_list[]")
        #print(rec_id_list)
        # rec_id = self.get_argument("rec_id",default="",strip=True)
        for rec_id in rec_id_list:
          operation = dnspod.RecordRemove(uemail, upwd, domain_id, rec_id)
          response = operation.request()

      elif oper == "disable" or oper == "enable" :
        rec_id = self.get_argument("rec_id",default="",strip=True)
        operation = dnspod.RecordStatus(uemail, upwd, domain_id,rec_id, oper)
        response = operation.request()
      
      elif oper == "modify":
        operation = dnspod.RecordModify(uemail, upwd, domain_id,
                                      self.get_argument("id").encode("UTF-8"),
                                      self.get_argument("sub_domain").encode("UTF-8"),
                                      self.get_argument("record_type").encode("UTF-8"),
                                      self.get_argument("line").encode("UTF-8"),
                                      self.get_argument("value").encode("UTF-8"),
                                      self.get_argument("ttl").encode("UTF-8"),
                                      self.get_argument("mx").encode("UTF-8"),
                                      )
        response = operation.request()
      elif oper == "import" :
        if self.request.files:  
            myfile = self.request.files['importFile'][0]  
            #fin = open("/home/zz/in.jpg","w")    
            #print "success to open file"  
            #fin.write(myfile["body"])
            #print(myfile["body"]);
            content = myfile["body"]
            lines = content.strip().split("\r\n");
            print(lines)
            if len(lines)>1:
              for i in range(1,len(lines)):
                raw_record = lines[i].strip().split(" ")
                print(raw_record)
                operation = dnspod.RecordCreate(uemail, upwd, domain_id,
                                      raw_record[0],
                                      raw_record[1],
                                      raw_record[2],
                                      raw_record[3],
                                      raw_record[4],
                                      raw_record[5],
                                      
                                      )
              response = operation.request()
              self.redirect("/domains/{0}/".format(domain_id))
      #print(response)

    self.write(json.dumps(response))

def main():
  tornado.options.parse_command_line()
  http_server = tornado.httpserver.HTTPServer(Application())
  http_server.listen(options.port)
  tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
  main()