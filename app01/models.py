from django.db import models

class User(models.Model):
    """
    用户表
    """
    username = models.CharField(verbose_name='用户名',max_length=32)
    password = models.CharField(verbose_name='密码',max_length=64)
    gender_choices = ((1,'男'),(2,'女'))
    gender = models.IntegerField(choices=gender_choices,default=1)
    roles = models.ManyToManyField(verbose_name='具有的所有角色',to="Role",blank=True)


class Role(models.Model):
    """
    角色表
    """
    title = models.CharField(max_length=32,verbose_name='职位角色')
    permissions = models.ManyToManyField(verbose_name='具有的所有权限',to='Permission',blank=True)

    class Meta:
        verbose_name_plural = "角色表"

    def __str__(self):
        return self.title


class Permission(models.Model):
    """
    权限表
    """
    title = models.CharField(verbose_name='url标题',max_length=32)
    url = models.CharField(verbose_name="含正则URL",max_length=64)
    code = models.CharField(verbose_name='url代码',max_length=32,default=0)  # 路径对应的描述名称

    class Meta:
        verbose_name_plural = "权限表"

    def __str__(self):
        return self.title
