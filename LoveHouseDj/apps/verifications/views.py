import re
import logging
import json
import random

from django.views import View
from django import http
from django_redis import get_redis_connection
from django.shortcuts import render

from utils import constants
from utils.response_code import RET
# 导入第三方包中的图形验证码生成方式
from verifications.libs.captcha.captcha import captcha
from verifications.libs.yuntongxun.ccp_sms import CCP


logger = logging.getLogger("log")


class ImageCodeView(View):
    """
    获取图片验证码
    """
    def get(self, request):
        """
        获取图片验证码
        :param request:
        :return:
        """
        # 1、获取参数
        cur_uuid = request.GET.get("cur", "")
        pre_uuid = request.GET.get("pre", "")

        # 2、校验参数
        if not cur_uuid:
            return http.HttpResponseForbidden("参数不全")

        if not re.match(r"\w{8}(-\w{4}){3}-\w{12}", cur_uuid):
            return http.HttpResponseForbidden("参数格式不正确")

        if pre_uuid and not re.match(r"\w{8}(-\w{4}){3}-\w{12}", pre_uuid):
            return http.HttpResponseForbidden("参数格式不正确")

        # 3、生成验证码
        text, image = captcha.generate_captcha()
        logger.info("图片验证码是：%s" % text)

        # 4、将生成的验证码保存在redis中
        redis_conn = get_redis_connection("verify_code")
        try:
            # 删除原来的
            redis_conn.delete("ImageCode_" + pre_uuid)
            # 保存当前的
            redis_conn.setex("ImageCode_" + cur_uuid, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError("生成图片验证码错误")
        else:
            return http.HttpResponse(image, content_type="image/jpg")


class SMSCodeView(View):
    """
    获取短信验证码
    """