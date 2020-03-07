from django.conf.urls import url

from homes import views

urlpatterns = [
    url(r'^login$', views.LoginViews.as_view()),
]