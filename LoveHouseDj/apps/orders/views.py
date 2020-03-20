import datetime
import logging
import json

from django import http
from django.shortcuts import render
from django.views import View
from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Q
from django.core.paginator import Paginator
from django_redis import get_redis_connection

from utils.response_code import RET
from utils import constants
from .models import Order
from homes.models import House


logger = logging.info("log")


class OrderSetViews(View):
    """
    创建订单
    """
    def post(self, request):
        """
        创建订单
        :param request:
        :return:
        """
        # 获取数据
        user = request.user
        user_id = user.id
        params_dict = json.loads(request.body)
        house_id = params_dict.get("house_id", 0)
        begin_date = params_dict.get("begin_date", "")
        end_date = params_dict.get("end_date", "")
        if not all([house_id,begin_date,end_date]):
            return http.JsonResponse({"errno": RET.DATAERR, "errmsg": "缺少参数"})
        try:
            house_obj = House.objects.get(id=house_id, room_count__gt=0)
        except Exception as e:
            logger.infor(e)
            return http.JsonResponse({"errno": RET.DATAERR, "errmsg": "参数错误"})

        # 是否是房主下单
        if user_id and user_id == house_obj.user_id:
            return http.JsonResponse({"errno": RET.PARAMERR, "errmsg": "房主无需下单"})

        new_time = datetime.date.today()
        if house_obj.room_count >0:
            order = Order.objects.filter(house_id=house_id,end_date__gt=new_time,user_id=user_id)
            if order:
                return http.JsonResponse({'errno':RET.DATAEXIST,'errmsg':'您已经预定该房间预定'})
        else:
            return http.JsonResponse({'errno': RET.DATAEXIST, 'errmsg': '该房子没房间了'})

        begin_date = datetime.datetime.strptime(begin_date, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        days = (end_date - begin_date).days
        if days == 0:
            days = 1
        elif days < house_obj.min_days:
            return http.JsonResponse({"errno": RET.DATAEXIST, "errmsg": "'该房间最少入住%s天"%house_obj.min_days})
        orders = Order.objects.create(
            user_id=user_id,
            house_id=house_id,
            begin_date=begin_date,
            end_date=end_date,
            days=days,
            house_price=0,
            amount=0,
            status=Order.ORDER_STATUS["WAIT_ACCEPT"],
        )

        orders.house_price = orders.house.price
        orders.amount = orders.house_price * days + house_obj.deposit
        # orders.amount = orders.house_price * days
        house_obj.room_count -= 1
        # 下单完成的订单数
        house_obj.order_count += 1
        orders.save()
        house_obj.save()
        return http.JsonResponse({"errno": RET.OK, "errmsg": "下单成功"})

    def put(self, request):
        return http.JsonResponse({"errno": RET.OK, "errmsg": "OK"})