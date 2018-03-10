from django.conf.urls import url,include
from django.db.models import Q
from django.shortcuts import render,redirect,HttpResponse
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.http import QueryDict
import copy
import json


class FilterOption(object):
    def __init__(self, field_name, multi=False, condition=None, is_choice=False):
        """
        :param field_name: 字段
        :param multi:  是否多选
        :param condition: 显示数据的筛选条件
        :param is_choice: 是否是choice
        """
        self.field_name = field_name
        self.multi = multi
        self.is_choice = is_choice

        self.condition = condition

    def get_queryset(self, _field):
        if self.condition:
            return _field.rel.to.objects.filter(**self.condition)
        return _field.rel.to.objects.all()

    def get_choices(self, _field):
        return _field.choices


class FilterRow(object):
    def __init__(self,option, data, request):
        self.data = data
        self.option = option
        # request.GET
        self.request = request


    def __iter__(self):
        params = copy.deepcopy(self.request.GET)
        params._mutable = True
        current_id = params.get(self.option.field_name) # 3
        current_id_list = params.getlist(self.option.field_name) # [1,2,3]

        if self.option.field_name in params:
            # del params[self.option.field_name]
            origin_list = params.pop(self.option.field_name)
            url = "{0}?{1}".format(self.request.path_info, params.urlencode())
            yield mark_safe('<a href="{0}">全部</a>'.format(url))
            params.setlist(self.option.field_name,origin_list)
        else:
            url = "{0}?{1}".format(self.request.path_info, params.urlencode())
            yield mark_safe('<a class="active" href="{0}">全部</a>'.format(url))
        # ( (1,男),(2,女)  )
        for val in self.data:
            if self.option.is_choice:
                pk,text = str(val[0]),val[1]
            else:
                pk,text = str(val.pk), str(val)
            # 当前URL？option.field_name
            # 当前URL？gender=pk
            # self.request.path_info # http://127.0.0.1:8005/arya/crm/customer/?gender=1&id=2
            # self.request.GET['gender'] = 1 # &id=2gender=1
            if not self.option.multi:
                # 单选
                params[self.option.field_name] = pk
                url = "{0}?{1}".format(self.request.path_info,params.urlencode())
                if current_id == pk:
                    yield mark_safe("<a class='active' href='{0}'>{1}</a>".format(url,text))
                else:
                    yield mark_safe("<a href='{0}'>{1}</a>".format(url, text))
            else:
                # 多选 current_id_list = ["1","2"]
                _params = copy.deepcopy(params)
                id_list = _params.getlist(self.option.field_name)

                if pk in current_id_list:
                    id_list.remove(pk)
                    _params.setlist(self.option.field_name, id_list)
                    url = "{0}?{1}".format(self.request.path_info, _params.urlencode())
                    yield mark_safe("<a class='active' href='{0}'>{1}</a>".format(url, text))
                else:
                    id_list.append(pk)
                    # params中被重新赋值
                    _params.setlist(self.option.field_name,id_list)
                    # 创建URL
                    url = "{0}?{1}".format(self.request.path_info, _params.urlencode())
                    yield mark_safe("<a href='{0}'>{1}</a>".format(url, text))



class ChangeList(object):
    '''封装信息页面的信息，原来的changelist视图函数'''
    def __init__(self,config,queryset):
        '''
        封装原来config类中视图函数中的内容
        :param config: 处理model类的config类
        :param queryset: 当前model表中的数据
        '''
        self.config = config   # 就是指config类
        self.queryset = queryset
        self.list_display = config.get_list_display()  # ['id','name','pwd']
        self.model_class = config.model_class
        self.request = config.request
        self.show_add_btn = config.get_show_add_btn()

        self.show_search_form = config.get_show_search_form() # 是否显示筛选框
        self.search_form_val =config.request.GET.get(self.config.search_key,'')  # 筛选的关键字

        self.actions = config.get_actions()
        self.show_actions = config.get_show_actions()   # 是否显示acitons

        self.comb_filter = config.get_comb_filter()     # 拿到配置的组合搜索的字段

        # 初始化时候，就处理分页,拿到数据
        from utils.pager import Pagination
        current_page = self.request.GET.get('page', 1)
        total_count = self.queryset.count()
        page_obj = Pagination(current_page, total_count,self.request.path_info, self.request.GET, per_page_count=2)
        self.page_obj = page_obj
        self.data_list = queryset[page_obj.start:page_obj.end]

    def head_list(self):
        '''构建表头'''
        head_list = []
        for field_name in self.list_display:
            if isinstance(field_name, str):
                verbose_name = self.model_class._meta.get_field(field_name).verbose_name
            else:
                verbose_name = field_name(self.config, is_head=True)
            head_list.append(verbose_name)
        return head_list

    def body_list(self):
        '''显示页面的数据'''
        new_data_list = []  # 创建用于页面渲染的数据结构
        for row in self.data_list:
            temp = []  # 每个model
            for field_name in self.list_display:  # self，就是指当前的config类的对象，
                if isinstance(field_name, str):
                    val = getattr(row, field_name)
                else:
                    val = field_name(self.config, row)  # 传入当前的model对象，为了拿到当前行的数据id
                temp.append(val)
            new_data_list.append(temp)
        return new_data_list

    def add_url(self):
        '''显示页面添加添加按钮的url'''
        return self.config.get_add_url()

    def modify_actions(self):
        '''获取定义的actions函数'''
        result = []
        for func in self.actions:
            temp = {'name': func.__name__, 'text': func.short_desc}
            result.append(temp)
        return result

    def gen_comb_filter(self):
        """
        生成器函数
        :return:
        """
        # ['gender','depart','roles']
        # self.model_class = > models.UserInfo

        """
        [
             FilterRow(((1,'男'),(2,'女'),)),
             FilterRow([obj,obj,obj,obj ]),
             FilterRow([obj,obj,obj,obj ]),
        ]
        """
        from django.db.models import ForeignKey, ManyToManyField
        for option in self.comb_filter:
            _field = self.model_class._meta.get_field(option.field_name)
            if isinstance(_field, ForeignKey):
                # 获取当前字段depart，关联的表 Department表并获取其所有数据
                # print(field_name,_field.rel.to.objects.all())
                row = FilterRow(option, option.get_queryset(_field), self.request)
            elif isinstance(_field, ManyToManyField):
                # print(field_name, _field.rel.to.objects.all())
                # data_list.append(  FilterRow(_field.rel.to.objects.all()) )
                row = FilterRow(option, option.get_queryset(_field), self.request)

            else:
                # print(field_name,_field.choices)
                # data_list.append(  FilterRow(_field.choices) )
                row = FilterRow(option, option.get_choices(_field), self.request)
            # 可迭代对象
            yield row


class StarkConfig(object):
    '''处理model对象的config基类'''
    def __init__(self,model_class,site):
        self.model_class = model_class  # 就是model类(表)
        self.site = site   # 也就是当前单例的对象

        self.request = None  # 在wrap方法中赋值，当用户访问视图函数时，调用wrap方法赋值。
        self._query_param_key = '_listfilter'
        self.search_key = "_q"  # 用于模糊搜索

    def get_urls(self):
        app_model_names = (self.model_class._meta.app_label,self.model_class._meta.model_name)
        li = [
            url(r'^$', self.wrap(self.changelist_view), name="%s_%s_changelist" % app_model_names),
            url(r'^add/$', self.wrap(self.add_view), name="%s_%s_add" % app_model_names),
            url(r'^delete/(\d+)$', self.wrap(self.delete_view), name="%s_%s_delete" % app_model_names),
            url(r'^edit/(\d+)$', self.wrap(self.edit_view), name="%s_%s_edit" % app_model_names),
        ]
        li.extend(self.get_extra_url())  # 自定义config中重写，用于在自定义config中为单独的model类扩展url
        return li

    @property
    def urls(self):
        return (self.get_urls(), None, None)

    # >>>>>>>> 1.配置页面显示的列信息 <<<<<<<<<<<<<<
    def edit(self, obj=None, is_head=False):
        if is_head:
            return '编辑'
        # 获取当前url上的筛选条件
        query_str = self.request.GET.urlencode()   # page=2&nid=1 str类型

        if query_str:
            # 重新构造
            params = QueryDict(mutable=True)
            params[self._query_param_key] = query_str
            return mark_safe(
                '<a href="%s?%s">编辑</a>' % (self.get_edit_url(obj.id), params.urlencode(),))  # /stark/app01/userinfo/
        return mark_safe('<a href="%s">编辑</a>' % (self.get_edit_url(obj.id),))  # /stark/app01/userinfo/

    def checkbox(self, obj=None, is_head=False):
        if is_head:
            return '选择'
        return mark_safe('<input type="checkbox" name="pk" value="%s" />' % (obj.id,))

    def delete(self, obj=None, is_head=False):
        if is_head:
            return '删除'
            # 反向生成url
        del_url = self.get_delete_url(obj.id)
        return mark_safe('<a href="%s">删除</a>' % del_url)


    # *********** URL相关 **********************
    # 反向生成增删改查的url
    def get_edit_url(self, nid):
        name = "%s_%s_edit" % (self.model_class._meta.app_label, self.model_class._meta.model_name,)
        edit_url = reverse(name, args=(nid,))
        return edit_url

    def get_list_url(self):
        name = "%s_%s_changelist" % (self.model_class._meta.app_label, self.model_class._meta.model_name,)
        list_url = reverse(name)
        return list_url

    def get_add_url(self):
        name = "%s_%s_add" % (self.model_class._meta.app_label, self.model_class._meta.model_name,)
        add_url = reverse(name)
        return add_url

    def get_delete_url(self, nid):
        name = "%s_%s_delete" % (self.model_class._meta.app_label, self.model_class._meta.model_name,)
        del_url = reverse(name, args=(nid,))
        return del_url

    def get_extra_url(self): # 用于扩展url
        return []

    def wrap(self,view_func):
        '''用于在编辑时传入self.request = request'''
        def inner(request,*args,**kwargs):
            self.request = request
            return view_func(request,*args,**kwargs)
        return inner

    # ############# 定义的功能 ################
    # >>>>>>>> 1.list_display 页面显示字段的配置 <<<<<<<<<<<<<<

    list_display = []
    def get_list_display(self):  # 这里可以在自己的config类中重写，以加上权限
        data = []
        if self.list_display:
            data.extend(self.list_display)
            data.append(StarkConfig.edit)  # edit是函数，调用时，需要加入对象
            data.append(StarkConfig.delete)
            data.insert(0, StarkConfig.checkbox)
        return data

    # >>>>>>>> 2.配置是否显示添加按钮 <<<<<<<<<<<<<<
    show_add_btn = True
    def get_show_add_btn(self):
        return self.show_add_btn

    # >>>>>>>> 3.配置添加、编辑时用到的Form类，用于验证、自动向数据库添加 <<<<<<<<<<<<<<
    model_form_class = None
    def get_model_form_class(self):
        if self.model_form_class:  # 如果有定制类
            return self.model_form_class

        from django.forms import ModelForm
        # 假如没有定制，就用ModeFrom，来根据表生成
        # 方式一：
        # class TestModelForm(ModelForm):
        #     class Meta:
        #         model = self.model_class
        #         fields = "__all__"
        # 方式二：type创建TestModelForm类
        meta = type('Meta', (object,), {'model': self.model_class, 'fields': '__all__'})
        TestModelForm = type('TestModelForm', (ModelForm,), {'Meta': meta})
        return TestModelForm

    # >>>>>>>> 4.搜索框 <<<<<<<<<<<<<<
    show_search_form = False
    def get_show_search_form(self):
        '''是否显示筛选框'''
        return self.show_search_form

    search_fields = []
    def get_search_fields(self):
        '''拿到筛选的字段设置'''
        result = []
        if self.search_fields:
            result.extend(self.search_fields)
        return result

    def get_search_condition(self):
        '''获取筛选条件'''

        key_word = self.request.GET.get(self.search_key)
        search_fields = self.get_search_fields()

        condition = Q()
        condition.connector = 'or'
        if key_word and self.get_show_search_form():
            for field_name in search_fields:
                condition.children.append((field_name, key_word))
        return condition

    # >>>>>>>> 5.定制actions <<<<<<<<<<<<<<
    show_actions = False         # 是否在页面新式actions
    def get_show_actions(self):
        return self.show_actions

    actions = []           # 用来放批量操作的函数
    def get_actions(self):
        result = []
        if self.actions:
            result.extend(self.actions)
        return result


    # >>>>>>>> 6.定制组合搜索 <<<<<<<<<<<<<<
    comb_filter = []
    def get_comb_filter(self):
        result = []
        if self.comb_filter:
            result.extend(self.comb_filter)
        return result



    # ############# 视图函数:处理请求的方法 ################

    def changelist_view(self, request, *args, **kwargs):
        '''页面显示视图'''
        if request.method == 'POST' and self.get_show_actions():
            func_name_str = request.POST.get('list_action')
            print(func_name_str,'function_actions_str')
            action_func = getattr(self, func_name_str)
            ret = action_func(request)
            if ret:
                return ret

        comb_condition = {}
        option_list = self.get_comb_filter()
        for key in request.GET.keys():
            value_list = request.GET.getlist(key)
            flag = False
            for option in option_list:
                if option.field_name == key:
                    flag = True
                    break

            if flag:
                comb_condition["%s__in" % key] = value_list

        queryset = self.model_class.objects.filter(self.get_search_condition()).filter(**comb_condition).distinct()

        # query_list = self.model_class.objects.filter(self.get_search_condition())    # 当前页的数据
        cls = ChangeList(self,queryset)  # 实例化，执行ChangeList类的__init__方法，里边封装了列表页面展示的信息

        return render(request,'stark/changelist.html',{'cl':cls})

    def add_view(self, request, *args, **kwargs):
        '''添加的视图函数'''
        model_form_class = self.get_model_form_class()
        _popbackid = request.GET.get('_popbackid')

        if request.method == "GET":
            form = model_form_class()
            print(form,'999999999999    ')
            return render(request, 'stark/add_view.html', {'form': form})
        else:
            form = model_form_class(request.POST)
            if form.is_valid():
                # 数据库中创建数据
                new_obj = form.save()
                if _popbackid:
                    # 是popup请求
                    # render一个页面，写自执行函数
                    result = {'id': new_obj.pk, 'text': str(new_obj), 'popbackid': _popbackid}
                    return render(request, 'stark/popup_response.html',
                                  {'json_result': json.dumps(result, ensure_ascii=False)})
                else:
                    return redirect(self.get_list_url())
            return render(request, 'stark/add_view.html', {'form': form})

    def edit_view(self, request, nid, *args, **kwargs):
        # self.model_class.objects.filter(id=nid)
        obj = self.model_class.objects.filter(pk=nid).first()
        if not obj:
            return redirect(self.get_list_url())

        model_form_class = self.get_model_form_class()
        # GET,显示标签+默认值
        if request.method == 'GET':
            form = model_form_class(instance=obj)
            return render(request, 'stark/edit_view.html', {'form': form})
        else:
            form = model_form_class(instance=obj, data=request.POST)
            if form.is_valid():
                form.save()
                list_query_str = request.GET.get(self._query_param_key)
                list_url = "%s?%s" % (self.get_list_url(), list_query_str,)
                return redirect(list_url)
            return render(request, 'stark/edit_view.html', {'form': form})

    def delete_view(self, request, nid, *args, **kwargs):
        '''删除的视图函数'''
        self.model_class.objects.filter(pk=nid).delete()
        return redirect(self.get_list_url())


class StarkSite(object):
    '''项目已启动，就执行了这个类中的属性，以及方法'''
    def __init__(self):
        self._registry = {}

    def register(self,model_class,stark_config=None):
        '''在每个app下边的stark.py文件中调用v1.site.register(),来注册了model类，以及要处理model类的config类'''
        if not stark_config:
            stark_config = StarkConfig
        self._registry[model_class] = stark_config(model_class,self) # 执行config类的__init__方法

    def get_urls(self):
        url_pattern = []
        for model_class,stark_config_obj in self._registry.items():
            app_name = model_class._meta.app_label  # app名称
            model_name = model_class._meta.model_name   # app应用下边的表名
            curd_url = url(r'{0}/{1}/'.format(app_name,model_name),include(stark_config_obj.urls))  # 分发,include参数是一个列表
            url_pattern.append(curd_url)
        return url_pattern

    @property
    def urls(self):
        ''''''
        return (self.get_urls(),None,None)

site =StarkSite()



