from django.conf.urls import url

from homes import views

urlpatterns = [
    url(r'^areas$', views.AreaViews.as_view()),
    url(r'^index$', views.IndexViews.as_view()),
    url(r'^houses$', views.HouseViews.as_view()),
]