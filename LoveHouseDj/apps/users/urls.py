from django.conf.urls import url

from users import views


urlpatterns = [
    url(r'^register$', views.RegisterView.as_view()),
    url(r'^login$', views.LoginViews.as_view()),
    url(r'^session$', views.LoginViews.as_view()),
    url(r'^my$', views.MyViews.as_view()),
]