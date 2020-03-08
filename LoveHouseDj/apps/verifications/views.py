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
    def post(self, request):
        """
        获取短信验证码
        :param request:
        :return:
        """
        # 1、获取参数
        params_dict = json.loads(request.body.decode())
        mobile = params_dict.get("mobile", "")
        image_code = params_dict.get("text", "")
        image_code_id = params_dict.get("id", "")

        # 2、校验参数
        # 2.1、检验手机号时候存在
        # 连接redis，检验手机号是否存在
        redis_conn = get_redis_connection("verify_code")
        sms_code_flag = redis_conn.get("sms_code_flag_%s" % mobile)
        if sms_code_flag:
            return http.JsonResponse({'error': RET.REQERR, 'errmsg': '请求过于频繁'})

        if not all([mobile, image_code, image_code_id]):
            return http.JsonResponse({"errno": RET.PARAMERR, "errmsg": "参数错误"})

        # 2.2、检验手机号时候合法
        if not re.match(r"^1[3-9]\d{9}", mobile):
            return http.JsonResponse({"errno": RET.PARAMERR, "errmsg": "参数错误"})

        # 2.3、验证码是否过期
        try:
            real_image_code = redis_conn.get("ImageCode_%s" % image_code_id)
            if not real_image_code:
                return http.JsonResponse({"errno": RET.NODATA, "errmsg": "验证码已经过期"})
            redis_conn.delete('ImageCode_' + image_code_id)
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({"errno": RET.DBERR, "errmsg": "数据库查询错误"})

        # 检验输入的验证码是否正确，因为存入redis的验证码为byte类型，所以需要decode()
        if image_code.upper() != real_image_code.decode().upper():
            return http.JsonResponse({"errno": RET.DATAERR, "errmsg": "验证码输入错误"})

        # 3、生成短信验证码
        sms_code = "%06d" % random.randint(0, 999999)
        logger.info("短信验证码为：%s" % sms_code)

        # 4、储存短信验证码
        pl = redis_conn.pipeline()
        pl.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex("sms_code_flag_%s" % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)
        pl.execute()

        # 5、通过第三方工具发送验证码，使用异步发送
        try:
            result = CCP().send_sms_code(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60], 1)
            # if result != 0:
            #     return http.JsonResponse({"errno": RET.THIRDERR, "errmsg": "第三方系统出错"})
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({"errno": RET.UNKOWNERR, "errmsg": "未知错误"})


        # 6、返回响应
        return http.JsonResponse({'errno': RET.OK, 'errmsg': '发送短信成功'})