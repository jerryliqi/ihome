import datetime
import logging

from django import http
from django.shortcuts import render
from django.views import View
from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Q

from utils.response_code import RET
from .models import Area, House
from orders.models import Order


logger = logging.getLogger("log")


class AreaViews(View):
    """
    选择城区功能
    """
    def get(self, request):
        """
        选择城区功能
        :param request:
        :return:
        """
        # 1、缓存中获取
        areas_list = cache.get("area_info", "")

        # 2、数据库获取
        if not areas_list:
            try:
                area_objs = Area.objects.all()
            except DatabaseError as e:
                logger.error(e)
                return http.JsonResponse({"errno": RET.DBERR, "errmsg": "数据库查询失败"})

            areas_list = [area.to_dict() for area in area_objs]

            cache.set("area_info", areas_list, 3600)

        return http.JsonResponse({"errno": RET.OK, "errmsg": "获取成功", "data": areas_list})


class IndexViews(View):
    """
    首页接口
    """
    def get(self, request):

        # houses_list = cache.get("house_index")
        # if not houses_list:
        try:
            houses = House.objects.order_by("-order_count")[0:5]
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({"errno": RET.DBERR, "errmsg": "数据库查询失败"})

        houses_list = [house.to_basic_dict() for house in houses]
        cache.set('house_index', houses_list, 3600)

        # 返回数据
        return http.JsonResponse({"errno": RET.OK, "errmsg": "OK", "data": houses_list})


class HouseViews(View):
    """
    房源信息展示及新增房源
    """
    def get(self, request):
        """
        搜索房源
        :param request:
        :return:
        """
        # 1、获取参数
        house_args = request.GET
        area_id = house_args.get("aid", "")
        start_date_str = house_args.get("sd", "")
        end_date_str = house_args.get("ed", "")
        # new(最新上线), booking(订单量), price-inc(价格低到高), price-des(价格高到低)
        sort_key = house_args.get("sk", "new")
        page = house_args.get("p", "1")

        # 2、参数处理
        try:
            page = int(page)
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({"errno": RET.PARAMERR, "errmsg": "参数错误"})

        # 时间格式处理
        try:
            start_date = None
            end_date = None
            if start_date_str:
                start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
            if end_date_str:
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
            if start_date and end_date:
                assert start_date < end_date, Exception("开始时间大于结束时间")
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({"errno": RET.PARAMERR, "errmsg": "参数错误"})

        # 3、查询符合条件房源信息
        # 通过入住时间排除已经下单的房间
        if start_date and end_date:
            house_order_objs = Order.objects.filter(Q(begin_date__gte=end_date) | Q(end_date__lte=start_date))
        elif start_date:
            house_order_objs = Order.objects.filter(end_date__lte=start_date)
        elif end_date:
            house_order_objs = Order.objects.filter(begin_date__gte=end_date)
        else:
            house_order_objs = []

        house_ids = [house_order_obj.house_id for house_order_obj in house_order_objs]
        print(house_ids)
        print(start_date, end_date)

        # 查找满足条件的房源
        # 对房源进行排序
        if area_id:
            house_objs = House.objects.filter(area=area_id).exclude(pk__in=house_ids)
            if sort_key == "booking":
                # 销量最高
                house_objs = house_objs.order_by("-order_count")
            elif sort_key == "price-inc":
                # 价格低到高
                house_objs = house_objs.order_by("price")
            elif sort_key == "price-des":
                # 价格高到低
                house_objs = house_objs.order_by("-price")
            else:
                # 默认最新上线
                house_objs = house_objs.order_by("-create_time")
        else:
            house_objs = []

        # 4、构造参数并返回

    def post(self, request):
        """
        房源信息新增
        :param request:
        :return:
        """