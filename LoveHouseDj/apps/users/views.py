import datetime
import json
import re
import logging
from hashlib import md5

from django import http
from django.shortcuts import render
from django.views import View
from django.contrib.auth import login, logout, authenticate
from django_redis import get_redis_connection

from .models import User
from utils.response_code import RET


logger = logging.getLogger("log")


class RegisterView(View):
    """
    用户注册功能
    """
    def post(self, request):
        """
        用户注册
        :param request:
        :return:
        """

        # 1、获取参数
        params_dict = json.loads(request.body.decode())
        mobile = params_dict.get("mobile", "")
        phone_code = params_dict.get("phonecode", "")
        password = params_dict.get("password", "")

        # 2、验证手机号是否合法
        if not re.match(r"^1[3-9]\d{9}", mobile):
            return http.JsonResponse({"errno": RET.PARAMERR, "errmsg": "参数错误"})

        # 3、验证短信验证码
        redis_conn = get_redis_connection("verify_code")
        real_phone_code = redis_conn.get('sms_%s' % mobile)
        if not real_phone_code:
            return http.JsonResponse({"errno": RET.NODATA, "errmsg": "短信验证码已经过期"})

        if real_phone_code.decode() != phone_code:
            return http.JsonResponse({"errno": RET.DATAERR, "errmsg": "短信验证码输入错误"})

        # 4、密码md5加密
        md5_ = md5()
        md5_.update(password.encode('utf-8'))
        md5_password = md5_.hexdigest()

        # 5、创建新用户
        user_data = {
            "mobile": mobile,
            "username": mobile,
            "password": md5_password,
        }

        try:
            user = User.objects.create_user(**user_data)
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({"errno": RET.DBERR, "errmsg": "注册失败"})

        # 保持状态
        login(request, user)

        return http.JsonResponse({"errno": RET.OK, "errmsg": "注册成功"})


class LoginViews(View):
    """
    用户登录功能
    """
    def get(self, request):
        """
        状态保持
        :param request:
        :return:
        """
        # 1、判断用户是否登录
        user = request.user
        # 2、对用户进行认证
        if not user.is_authenticated:
            return http.JsonResponse({"errno": RET.SESSIONERR, "errmsg": "用户未登录"})

        data = {
            "user_id": user.id,
            "name": user.username
        }
        return http.JsonResponse({"errno": RET.OK, "errmsg": "已登录", "data": data})

    def post(self, request):
        """
        获取用户名、密码
        :param request:
        :return:
        """
        user_dict = json.loads(request.body.decode())
        mobile = user_dict.get("mobile", "")
        password = user_dict.get("password", "")
        # 1、参数检验
        # 1.1、参数不全
        if not all([mobile, password]):
            return http.JsonResponse({"errno": RET.PARAMERR, "errmsg": "参数不全"})

        # 1.2、密码是否符合位数（6-20个字母加数字）
        if not re.match(r"^[0-9a-zA-Z]{6,20}$", password):
            return http.JsonResponse({"errno": RET.PARAMERR, "errmsg": "请输入正确的用户名密码"})

        # 将密码md5加密
        md5_ = md5()
        md5_.update(password.encode('utf-8'))
        md5_password = md5_.hexdigest()

        # 用户是否存在
        user = authenticate(username=mobile, password=md5_password)
        if not user:
            return http.JsonResponse({"errno": RET.LOGINERR, "errmsg": "请输入正确的用户名密码"})

        # 状态保持
        login(request, user)
        return http.JsonResponse({"errno": RET.OK, "errmsg": "登录成功"})

    def delete(self, request):
        """
        退出登录
        :param request:
        :return:
        """


class MyViews(View):
    """
    我的主页
    """