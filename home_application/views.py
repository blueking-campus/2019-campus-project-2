# -*- coding: utf-8 -*-
import json

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import transaction
from django.http import JsonResponse, response, HttpResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.generic import View

from bkoauth.jwt_client import JWTClient
from bkoauth.utils import transform_uin
from common.context_processors import mysetting
from common.mymako import render_mako_context, render_json
from bkoauth.client import oauth_client
import logging
# 开发框架中通过中间件默认是需要登录态的，如有不需要登录的，可添加装饰器login_exempt【装饰器引入from account.decorators import login_exempt】
from common.utils import html_escape
from home_application.decorators import require_admin
from home_application.models import Organizations, Awards
from home_application.utils import valid_organization, valid_award, valid_apply


def home(request):
    """
    首页
    """
    return render_mako_context(request, '/home_application/home.html')


def dev_guide(request):
    """
    开发指引
    """
    return render_mako_context(request, '/home_application/dev_guide.html')


def contact(request):
    """
    联系我们
    """
    return render_mako_context(request, '/home_application/contact.html')


"""
组织管理api {start}
"""

"""
@api {get} /user
@apiDescription 获取用户信息
@apiGroup all user
@apiSuccessExample {json} Success-Response:
    {

        'nick': 用户昵称,
        'avatar': 用户头像,
        'permission': [
            'admin',
            'head',
            'apply'
        ]
    }

"""


@require_GET
def user_info(request):
    uin = request.COOKIES.get('uin', '')
    user_qq = transform_uin(uin)
    user = request.user
    permission = ['apply']
    if user.is_admin():
        permission.append('admin')
    if user.is_head(user_qq):
        permission.append('head')

    setting = mysetting(request)
    data = {
        'nick': setting['NICK'],
        'avatar': setting['AVATAR'],
        'permission': permission
    }
    return render_json(data)


"""
@api {POST} /organization
@apiDescription 创建一个组织
@apiGroup admin

@apiParam {String} name 组织名称
@apiParam {Array}  head 负责人
@apiParam {Array}  eva_member 评议人员
@apiParamExample {json} Request-Example:
    {
        name: "蓝鲸",
        head: [
            "7047xxxxx",
            "2234xxxxx",
        ],
        eva_member: [
            "xxxxxx",
            "xxxxxx",
        ]
    }
"""


@require_admin
@require_POST
def create_organization(request):
    data = {}
    try:
        data = json.loads(request.body)
        valid_organization(data)
    except Exception as e:
        return HttpResponse(status=422, content=u'%s' % e.message)

    try:
        Organizations.objects.create_organization(data, request.user)
    except Exception as e:
        return HttpResponse(status=400, content=u'%s' % e)

    return HttpResponse(status=201)


"""
分发 get delete put请求
"""


class OrganizationView(View):
    http_method_names = ['get', 'delete', 'put']

    @require_admin
    def get(self, request, organization_id):
        return get_organization(request, organization_id)

    @require_admin
    def delete(self, request, organization_id):
        return del_organization(request, organization_id)

    @require_admin
    def put(self, request, organization_id):
        return update_organiztion(request, organization_id)


@require_http_methods(["GET", "DELETE", "PUT"])
def organization_get_put_delete(request, organization_id):
    if not request.user.is_admin():
        return HttpResponse(status=401, content=u'无此权限')
    if request.method == "GET":
        return get_organization(request, organization_id)
    if request.method == "DELETE":
        return del_organization(request, organization_id)
    if request.method == "PUT":
        return update_organiztion(request, organization_id)


"""
@api {GEt} /organizations?page=?
@apiDescription 查询组织
@apiGroup admin

@apiParam {String} page 第几页 不存在为第一页
@apiSuccessExample {json} Success-Response:
    {
        "counts": "xxxx",
        "organizations":  [{
            id: 'xxx'
            name: '蓝鲸'，
            head: ['xxx', 'xxx'],
            eva_member: ['xxxx','xxx'],
            create_time: 'xxxx'
        }]
    }
"""


@require_admin
@require_GET
def organizations(request):
    organization_all = Organizations.objects.all()
    paginator = Paginator(organization_all, 10)
    page = request.GET.get('page', 1)
    try:
        organizations = paginator.page(page)
    except PageNotAnInteger:
        organizations = paginator.page(1)
    except EmptyPage:
        organizations = paginator.page(paginator.num_pages)
    return render_json({'counts': paginator.count, 'organizations': Organizations.to_array(organizations)})


"""
@api {GET} /organization/:id
@apiDescription 查询组织
@apiGroup admin

@apiParam {String} id 组织id
@apiSuccessExample {json} Success-Response:
    {

        id: 'xxx',
        name: '蓝鲸'，
        head: ['xxx', 'xxx'],
        eva_member: ['xxxx','xxx'],
        create_time: 'xxxx'
    }
"""


def get_organization(request, organization_id):
    try:
        organization = Organizations.objects.get(id=organization_id)
    except Exception as e:
        return HttpResponse(status=404)

    return render_json(organization.to_json())


"""
@api {PUT} /organization/:id
@apiDescription 更新组织信息
@apiGroup admin

@apiParam {String} name 组织名称
@apiParam {Array}  head 负责人
@apiParam {Array}  eva_member 评议人员
@apiParamExample {json} Request-Example:
    {
        name: "蓝鲸",
        head: [
            "7047xxxxx",
            "2234xxxxx",
        ],
        eva_member: [
            "xxxxxx",
            "xxxxxx",
        ]
    }
"""


def update_organiztion(request, organization_id):
    data = {}
    try:
        data = json.dumps(request.body)
        valid_organization(data)
    except Exception as e:
        return HttpResponse(status=422, content=u'%s' % e.message)

    organization = {}
    try:
        organization = Organizations.objects.get(id=organization_id)
        Organizations.objects.update_organization(
            organization, data, request.user)
    except Exception as e:
        return HttpResponse(status=400)

    return HttpResponse(status=201)


"""
@api {DELETE} /organization/:id
@apiDescription 删除组织
@apiGroup admin
"""


def del_organization(request, organization_id):
    organization = {}
    try:
        organization = Organizations.objects.get(id=organization_id)
        organization.delete()
    except Exception as e:
        return HttpResponse(status=410)

    return HttpResponse(status=204, content=u'删除成功')


"""
组织管理api {end}
"""


"""
奖项管理api {start}
"""


"""
@api {POST} /award
@apiDescription 创建一个奖项
@apiGroup admin

@apiParam {String} name 奖项名称 非法字符过滤
@apiParam {Array}  content 评价条件 需要xss过滤
@apiParam {String}  level 奖项级别 0: 中心级 1：部门级 2：小组级 4：公司级
@apiParam {Number}  organization 所属组织id
@apiParam {String}  start_time 开始时间
@apiParam {String}  end_time 结束时间
@apiParam {Bool}  have_attachment 是否允许附件
@apiParam {Bool}  is_active 是否生效

@apiGroup admin

@apiParamExample {json} Request-Example:
    {
        name: "蓝鲸",
        content: "xxxxxx", // 富文本
        level: "0",
        organization: "23",
        start_time: "2014-12-31 18:20:1",
        end_time: "2014-12-31 18:20:1",
        have_attachment: true,
        is_active: true,
    }
"""


@require_POST
@require_admin
def create_award(request):
    data = {}
    try:
        data = json.loads(request.body)
        valid_award(data)
    except Exception as e:
        return HttpResponse(status=422, content=u'%s' % e.message)

    try:
        Awards.objects.create(data)
    except Exception as e:
        return HttpResponse(status=400, content=u'%s' % e)

    return HttpResponse(status=201)


"""
分发 get delete put请求
"""


class AwardView(View):
    http_method_names = ['get', 'delete', 'put']

    @require_admin
    def get(self, request, organization_id):
        return get_award(request, organization_id)

    @require_admin
    def delete(self, request, organization_id):
        return del_award(request, organization_id)

    @require_admin
    def put(self, request, organization_id):
        return update_award(request, organization_id)


"""
@api {GET} /awards?page=?
@apiDescription 查询奖项
@apiGroup admin

@apiParam {String} page 第几页 不存在为第一页
@apiSuccessExample {json} Success-Response:
    {
        "counts": "15",
        "awards":  [{
            id: 'xxx'
            name: '季度之星'
            organization: '蓝鲸'，
            level: '0'，
            is_active: True，
            start_time: '2014-12-31 18:20:1'，
            apply_count: '10'，
            apply_award_count: '10'，
        }]
    }
"""


@require_admin
@require_GET
def awards(request):
    award_all = Awards.objects.all()
    paginator = Paginator(award_all, 10)
    page = request.GET.get('page', 1)
    try:
        awards = paginator.page(page)
    except PageNotAnInteger:
        awards = paginator.page(1)
    except EmptyPage:
        awards = paginator.page(paginator.count)
    return render_json(
        Awards.to_array({'counts': paginator.count, 'awards': awards}))


"""
@api {GET} /award/:id
@apiDescription 查询奖项
@apiGroup admin

@apiParam {Number} id 奖项id
@apiSuccessExample {json} Success-Response:
    {
        id: 'xxx'
        name: '季度之星'
        organization: '蓝鲸'，
        content: 'xxxxxx'，
        heads: ['xxx', 'xxxx']，
        level: '0'，
        is_active: True，
        start_time: '2014-12-31 18:20:1'，
        end_time: '2014-12-31 18:20:1'，
        applys: [{
            name: 'xxx',
            state: '1',
            apply_des: 'xxxxx',
            apply_time: '2014-12-31 18:20:1'，
            attachment: 'x',
            remark: 'xxxx'
        }]
    }
"""


def get_award(request, award_id):
    try:
        award = Awards.objects.get(id=award_id)
    except Exception as e:
        return HttpResponse(status=404)

    return render_json(award.to_json())


"""
@api {PUT} /award/:id
@apiDescription 更新奖项信息
@apiGroup admin

@apiParam {String} name 奖项名称 非法字符过滤
@apiParam {Array}  content 评价条件 需要xss过滤
@apiParam {String}  level 奖项级别 0: 中心级 1：部门级 2：小组级 4：公司级
@apiParam {Number}  organization 所属组织id
@apiParam {String}  start_time 开始时间
@apiParam {String}  end_time 结束时间
@apiParam {Bool}  have_attachment 是否允许附件
@apiParam {Bool}  is_active 是否生效


@apiParamExample {json} Request-Example:
    {
        name: "蓝鲸",
        content: "xxxxxx", // 富文本
        level: "0",
        organization: "23",
        start_time: "2014-12-31 18:20:1",
        end_time: "2014-12-31 18:20:1",
        have_attachment: true,
        is_active: true,
    }
"""


def update_award(request, award_id):
    data = {}
    try:
        data = json.dumps(request.body)
        valid_award(data)
    except Exception as e:
        return HttpResponse(status=422, content=u'%s' % e.message)

    award = {}
    try:
        award = Awards.objects.get(id=award_id)
        award.objects.update(data)
    except Exception as e:
        return HttpResponse(status=400)

    return HttpResponse(status=201)


"""
@api {DELETE} /award/:id
@apiDescription 删除奖项
@apiGroup admin
"""


def del_award(request, award_id):
    award = {}
    try:
        award = Awards.objects.get(id=award_id)
        award.delete()
    except Exception as e:
        return HttpResponse(status=410)

    return HttpResponse(status=204, content=u'删除成功')


"""
@api {GET} /award/organizations
@apiDescription 查询组织名录
@apiGroup admin


@apiSuccessExample {json} Success-Response:
    {
        "result": "John",
        "message":  [{
            id: 'xxx'
            name: '蓝鲸'，
        }]
    }
"""


@require_admin
@require_GET
def get_award_organizations(request):
    try:
        organizations = Organizations.objects.all()
    except:
        return HttpResponse(status=404)
    ret = []
    for item in organizations:
        ret.append({
            'id': item.id,
            'name': item.name
        })
    return render_json(ret)


"""
@api {POST} /awards/clone
@apiDescription 批量克隆奖项
@apiGroup admin

@apiParam {String} name 奖项名称 非法字符过滤
@apiParam {Array}  content 评价条件 需要xss过滤
@apiParam {String}  level 奖项级别 0: 中心级 1：部门级 2：小组级 4：公司级
@apiParam {Number}  organization 所属组织id
@apiParam {String}  start_time 开始时间
@apiParam {String}  end_time 结束时间
@apiParam {Bool}  have_attachment 是否允许附件
@apiParam {Bool}  is_active 是否生效

@apiGroup admin

@apiParamExample {json} Request-Example:
    [{
        name: "蓝鲸",
        content: "xxxxxx", // 富文本
        level: "0",
        organization: "23",
        start_time: "2014-12-31 18:20:1",
        end_time: "2014-12-31 18:20:1",
        have_attachment: true,
        is_active: true,
    }]



"""


@require_POST
@require_admin
@transaction.atomic
def awards_clone(request):
    """
    需要事务保证批量操作
    :param request:
    :return:
    """
    data = {}
    try:
        data = json.loads(request.body)
        for item in data:
            valid_award(item)
    except Exception as e:
        return HttpResponse(status=422, content=u'%s' % e.message)

    try:
        for item in data:
            Awards.objects.create(item)
    except Exception as e:
        return HttpResponse(status=400, content=u'%s' % e)

    return HttpResponse(status=201)


"""
奖项管理api {end}
"""


"""
我的申请api {start}
"""


"""
@api {GET} /my/applys/?page=?
@apiDescription 查询组织
@apiGroup admin

@apiParam {Number} page 第几页 无 默认第一页
@apiSuccessExample {json} Success-Response:
    {
        "counts": "15",
        "awards":  [{
            apply_id: 'xxx'
            apply_info: '季度之星'
            award_id: '12'，
            organization: 'xxxx'，
            apply_award: 'xxx'，
            award_state: True or False，
            state: '0'，-1 未申报 0 申报中 1 未通过 2 已通过 3未获奖 4 已获奖
            apply_time: '2014-12-31 18:20:1'，
        },
        {
            award_id: 'xx',
            organization: 'xxx',
            apply_award: 'xxx',
            award_state: 'xxx',
            state: 'xxx',
        }
        ]
    }
"""



@require_GET
def my_applys(request):
    """
    对django 模型跨表查询 不怎么熟悉 暂且使用 后期视性能优化
    :param request:
    :return:
    """
    uin = request.COOKIES.get('uin', '')
    user_qq = transform_uin(uin)
    user = request.user
    not_applys = user.get_my_not_apply(user_qq)
    applys = user.get_my_apply(user_qq)
    applys.extend(not_applys)
    paginator = Paginator(applys, 10)
    page = request.GET.get('page', 1)
    try:
        my_applys = paginator.page(page)
    except PageNotAnInteger:
        my_applys = paginator.page(1)
    except EmptyPage:
        my_applys = paginator.page(paginator.count)
    return render_json(
        Awards.to_array({'counts': paginator.count, 'my_applys': my_applys}))


"""
@api {POST} /my/apply/:id
@apiDescription 创建一个奖项
@apiGroup admin

@apiParam {Number} id 申请的奖项id
@apiParam {Array}  content 评价条件 需要xss过滤
@apiParam {String}  level 奖项级别 0: 中心级 1：部门级 2：小组级 4：公司级
@apiParam {Number}  organization 所属组织id
@apiParam {String}  start_time 开始时间
@apiParam {String}  end_time 结束时间
@apiParam {Bool}  have_attachment 是否允许附件
@apiParam {Bool}  is_active 是否生效

@apiGroup admin

@apiParamExample {json} Request-Example:
    {
        apply_info: "申报人/团队", 非法字符校验
        content: "事迹介绍", // xss 过滤 非法字符校验
        attachment_id: "233",
    }
"""

def apply_award(request, award_id):
    data = {}
    try:
        json = html_escape(request.body, is_json=True)
        data = json.loads(json)
        valid_apply(data)
    except Exception as e:
        return HttpResponse(status=422, content=u'%s' % e.message)
    try:
        Awards.objects.create(apply_info=data['apply_info'], apply_des=data['apply_info'], attachment_id=data['attachment_id'], award_id=award_id)
    except Exception as e:
        return HttpResponse(status=400, content=u'%s' % e)

    return HttpResponse(status=201)






"""
@api {POST} /my/apply/:id
@apiDescription 创建一个奖项
@apiGroup admin

@apiParam {Number} id 申请的奖项id
@apiParam {Array}  content 评价条件 需要xss过滤
@apiParam {String}  level 奖项级别 0: 中心级 1：部门级 2：小组级 4：公司级
@apiParam {Number}  organization 所属组织id
@apiParam {String}  start_time 开始时间
@apiParam {String}  end_time 结束时间
@apiParam {Bool}  have_attachment 是否允许附件
@apiParam {Bool}  is_active 是否生效

@apiGroup admin

@apiParamExample {json} Request-Example:
    {
        apply_info: "申报人/团队", 非法字符校验
        content: "事迹介绍", // xss 过滤 非法字符校验
        attachment_id: "233",
    }
"""

def upload_attachment():

    pass





"""
我的申请api {end}
"""
