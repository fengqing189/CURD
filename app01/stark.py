from stark.service import v1
from django.shortcuts import HttpResponse,render,redirect
from stark.service.v1 import StarkConfig
from django.forms import ModelForm
from django.conf.urls import url
from . import models

# 定制的用户编辑、添加时用到的modelForm类
class UserModelFrom(ModelForm):
    class Meta:
        model = models.User
        fields = ['username','gender','roles']
        error_messages = {}

class UserConfig(StarkConfig):
    # 1.定制页面显示的字段
    def display_roles(self,obj=None,is_head=None):
        '''定义角色字段显示的内容'''
        if is_head:
            return '角色'
        role_list = obj.roles.all()
        li = []
        for role in role_list:
            li.append(role.title)
        roles_str = ','.join(li)
        return roles_str

    def display_gender(self,obj=None,is_head=None):
        if is_head:
            return '性别'
        return obj.get_gender_display()

    list_display = ['id','username',display_gender,display_roles]
    # def get_list_display(self):pass  # 重写父类的方法可用来加权限，每个用户看到的字段不一样

    # 2.显示添加按钮
    show_add_btn = True
    # def get_show_add_btn(self):pass    #　重写基类的方式，可以在这里从数据库查询一下权限，看当前用户是否可以显示add按钮

    # 3.定义添加、编辑时，使用的Form验证类
    model_form_class = UserModelFrom    # 定制用户编辑、添加时用到的modelForm类

    # 4.自定义当前model表增加的url
    def get_extra_url(self):
        app_model_name = (self.model_class._meta.app_label,self.model_class._meta.model_name)
        urls = [
            url(r'^report/',self.report_view,name='%s_%s_report'%app_model_name),
        ]
        return urls

    def report_view(self,request,*args,**kwargs):
        '''自定制的report视图函数'''
        return HttpResponse('报告信息')

    # 5.定义搜索框搜索的字段
    show_search_form = True    #　是否显示筛选框
    search_fields = ['id__contains','username__contains',]

    # 6.自定义是否显示actions框，以及批量操作的方法
    # 自定义批量操作的函数actions
    show_actions = True

    def multi_del(self, request):
        pk_list = request.POST.getlist('pk')
        self.model_class.objects.filter(id__in=pk_list).delete()
        return redirect(self.get_list_url())  # 删除成功之后，要跳转的页面
    multi_del.short_desc = "批量删除"        # 函数也是对象，给函数对象加个属性

    actions = [multi_del,]

    # 7.自定义多重筛选(配置当前表根据那几个字段做组合搜索)
    # comb_filter = ['gender','roles']

    comb_filter = [
        v1.FilterOption('gender', is_choice=True),
        # v1.FilterOption('depart', condition={'id__gt': 3}),
        v1.FilterOption('roles', True),
    ]

v1.site.register(models.User,UserConfig)



class RoleConfig(StarkConfig):
    list_display = ['id','title']

v1.site.register(models.Role,RoleConfig)