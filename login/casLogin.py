import json
import re
import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning
from login.Utils import Utils

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class casLogin:
    # 初始化cas登陆模块
    def __init__(self, username, password, login_url, host, session):
        self.username = username
        self.password = password
        self.login_url = login_url
        self.host = host
        self.session = session
        self.type = 0

    # 判断是否需要验证码
    def getNeedCaptchaUrl(self):
        if self.type == 0:
            url = self.host + 'authserver/needCaptcha.html' + '?username=' + self.username
            flag = self.session.get(url, verify=False).text
            return 'false' != flag and 'False' != flag
        else:
            url = self.host + 'authserver/checkNeedCaptcha.htl' + '?username=' + self.username
            flag = self.session.get(url, verify=False).json()
            return flag['isNeed']

    def login(self):
        html = self.session.get(self.login_url, verify=False).text
        soup = BeautifulSoup(html, 'lxml')
        form = soup.select('#casLoginForm')
        if len(form) == 0:
            form = soup.select("#loginFromId")
            if len(form) == 0:
                raise Exception('出错啦！网页中没有找到casLoginForm')
            soup = BeautifulSoup(str(form[1]), 'lxml')
            self.type = 1
        # 填充数据
        params = {}
        form = soup.select('input')
        for item in form:
            if None != item.get('name') and len(item.get('name')) > 0:
                if item.get('name') != 'rememberMe':
                    if None == item.get('value'):
                        params[item.get('name')] = ''
                    else:
                        params[item.get('name')] = item.get('value')
        if self.type == 0:
            salt = soup.select("#pwdDefaultEncryptSalt")
        else:
            salt = soup.select("#pwdEncryptSalt")
        if len(salt) != 0:
            salt = salt[0].get('value')
        else:
            pattern = '\"(\w{16})\"'
            salt = re.findall(pattern, html)
            if (len(salt) != 0):
                salt = salt[1]
            else:
                salt = False
        print(salt)
        params['username'] = self.username
        if not salt:
            params['password'] = self.password
        else:
            params['password'] = Utils.encryptAES(self.password, salt)
            if self.getNeedCaptchaUrl():
                if self.type == 0:
                    imgUrl = self.host + 'authserver/captcha.html'
                    params['captchaResponse'] = Utils.getCodeFromImg(self.session, imgUrl)
                else:
                    imgUrl = self.host + 'authserver/getCaptcha.htl'
                    params['captcha'] = Utils.getCodeFromImg(self.session, imgUrl)
        data = self.session.post(self.login_url, params=params, allow_redirects=False)
        print("ss",data.status_code)
        # 如果等于302强制跳转，代表登陆成功
        if data.status_code == 302:
            jump_url = data.headers['Location']
            self.session.headers['Server'] = 'CloudWAF'
            res = self.session.get(jump_url, verify=False)
            if res.status_code == 200:
                return self.session.cookies
            else:
                print(res,"ress")
                res = self.session.get(re.findall(r'\w{4,5}\:\/\/.*?\/', self.login_url)[0], verify=False)
                
                if res.status_code == 200 or res.status_code == 404:
                    return self.session.cookies
                else:
                    raise Exception('登录失败，请反馈BUG')
        elif data.status_code == 200:
            data = data.text
            soup = BeautifulSoup(data, 'lxml')
            print(data,self.type)
            if self.type == 0:
                print('485489465156')
                msg = soup.select('#errorMsg')[0].get_text()
                msg='smwy'
                print(msg)
            else:
                msg = soup.select('#formErrorTip2')[0].get_text()
            raise Exception(msg)
        else:
            raise Exception('教务系统出现了问题啦！返回状态码：' + str(data.status_code))
