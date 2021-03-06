# coding=utf-8
from __future__ import unicode_literals
import json
import operator
import os
import re

from django import forms
from django.conf import settings

from common.pxfilter import XssHtml
from common.utils import html_escape
from functools import reduce

from .models import OrganizationsUser, Awards, MyApply, Organizations


class InvalidData(Exception):
    pass


def valid_organization(data):
    if data['name'] != '':
        pass
        # if re.match(
        #         r'^[\s\u4e00-\u9fa5a-z0-9_-]{0,}$',
        #         data['name']) is not None:
        #     raise Exception(u'含有非法字符')
    else:
        raise InvalidData(u'组织名字不能为空')

    if len(data['head']) == 0 or len(data['eva_member']) == 0:
        raise InvalidData(u'负责人或评价人员不能为空')

    data = json.loads(html_escape(json.dumps(data), is_json=True))


def valid_award(data):
    if data['name'] != '':
        pass
        # if re.match(
        #         r'^[\s\u4e00-\u9fa5a-z0-9_-]{0,}$',
        #         data['name']) is not None:
        #     raise Exception(u'含有非法字符')
    else:
        raise InvalidData(u'奖项名字不能为空')

    for k, v in data.items():
        if v == '' or v is None:
            raise InvalidData(u'不能为空')

    # 验证时xss富文本过滤
    parser = XssHtml()
    parser.feed(data['content'])
    parser.close()
    data['content'] = parser.getHtml()
    data['name'] = html_escape(data['name'])


def valid_clone(data):
    a = {}
    for k, v in data.items():
        if v == '' or v is None:
            raise InvalidData(u'不能为空')


def valid_apply(data):
    for k, v in data.items():
        if v == '' or v is None:
            raise InvalidData(u'不能为空')

    data = json.loads(html_escape(json.dumps(data), is_json=True))


def valid_decide(data):
    for k, v in data.items():
        if v == '' or v is None:
            raise InvalidData(u'不能为空')
    data = json.loads(html_escape(json.dumps(data), is_json=True))


def is_head(self, user_qq):
    """
    是否负责人
    """
    if self.is_superuser:
        return True
    return OrganizationsUser.objects.filter(
        user=user_qq, type=u'0').exists()


def is_organ_head(self, user_qq, organ):
    """
    是否该组织head
    :param user_qq:
    :return:
    """
    if self.is_superuser:
        return True
    return OrganizationsUser.objects.filter(
        user=user_qq, type=u'0', organization=organ).exists()


def get_my_not_apply(self, user_qq):
    applys, organs, __ = get_my_applys(self, user_qq)
    not_awards_id = [item.award.id for item in applys]
    not_awards = Awards.objects.exclude(
        id__in=not_awards_id,
        is_active=True).filter(
        soft_del=False,
        organization__soft_del=False,
        organization__in=organs).order_by('-id').all()

    ret = []
    for item in not_awards:
        ret.append({
            'award_id': item.id,
            'organization': item.organization.name,
            'apply_award': item.name,
            'award_state': item.is_active,
            'state': '-1',
            'count': MyApply.objects.filter(award=item).count()
        })
    return ret


def get_my_applys(self, user_qq, query=[]):
    organs = Organizations.objects.filter(
        organizationsuser__type=u'1',
        organizationsuser__user=user_qq).all()
    awards = Awards.objects.filter(
        organization__in=organs,
        soft_del=False).all()

    applys = MyApply.objects.filter(
            award__in=awards, user=self).all()
    filter_applys= []
    if len(query) > 0:
        filter_applys = MyApply.objects.filter(
            reduce(operator.or_, query),
            award__in=awards, user=self).all()
    return applys, organs, filter_applys


def get_my_apply(self, user_qq, apply_Q_list, is_not=False):
    applys, organs, filter_query = get_my_applys(self, user_qq, apply_Q_list)
    not_awards_id = [item.award.id for item in applys]
    not_awards = Awards.objects.exclude(
        id__in=not_awards_id,
        is_active=True).filter(
        soft_del=False,
        organization__soft_del=False,
        organization__in=organs).order_by('-id').all().select_related('organization')
    ret = []
    for item in not_awards:
        ret.append({
            'award_id': item.id,
            'organization': item.organization.name,
            'apply_award': item.name,
            'award_state': item.is_active,
            'state': '-1',
            'apply_id': None,
            'apply_info': None,
            'apply_time': None
        })

    if is_not:
        return ret

    if len(apply_Q_list) > 0:
        ret = []
        applys = filter_query

    for item in applys:
        ret.append({
            'apply_id': item.id,
            'apply_info': item.apply_info,
            'award_id': item.award.id,
            'organization': item.award.organization.name,
            'apply_award': item.award.name,
            'award_state': item.award.is_active,
            'state': item.state,
            'apply_time': item.apply_time.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return ret

    # awards = Awards.objects.raw(
    #     'select `awards`.id from `awards` join `organizations` o on `awards`.`organization_id` = `o`.`id` join `home_application_organizationsuser` `hao` on `o`.`id` = `hao`.`organization_id` where `hao`.`type` = \'1\' and o.soft_del = 0 and `hao`.`user` = %s',
    #     [user_qq])
    # awards = [str(item.id) for item in awards]
    # if len(awards) > 0:
    #     awards = ','.join(awards)
    #     awards = '  `awards`.`id` in (' + awards + ') and '
    # else:
    #     return []
    # # if len(apply_Q_list) > 0:
    # #     applys = MyApply.objects.filter(
    # #         reduce(
    # #             operator.or_,
    # #             apply_Q_list),
    # #         award_id__in=awards).order_by('-id').all()
    # # else:
    # #     applys = MyApply.objects.filter(award_id__in=awards).order_by('-id').all()
    # if len(apply_Q_list) > 0:
    #     applys = MyApply.objects.raw(
    #         'select `awards`.`id`,`awards`.id as award_id, `my_applys`.id as apply_id, `my_applys`.`apply_info`, `o`.`name`, `awards`.`name` as apply_award, `awards`.`is_active` as award_state, `my_applys`.`state`, `my_applys`.`apply_time` from `awards` left join `my_applys` on `awards`.`id` = `my_applys`.`award_id` join organizations o on awards.organization_id = o.id' +
    #         sql_where_list +
    #         awards +
    #         ' `awards`.`soft_del` = 0 and `o`.`soft_del` = 0 order by award_id desc',
    #         apply_Q_list)
    # else:
    #     applys = MyApply.objects.raw(
    #         'select `awards`.`id`,`awards`.id as award_id, `my_applys`.id as apply_id, `my_applys`.`apply_info`, `o`.`name`, `awards`.`name` as apply_award, `awards`.`is_active` as award_state, `my_applys`.`state`, `my_applys`.`apply_time` from `awards` left join `my_applys` on `awards`.`id` = `my_applys`.`award_id` join organizations o on awards.organization_id = o.id' +
    #         sql_where_list +
    #         awards +
    #         ' `awards`.`soft_del` = 0 and `o`.`soft_del` = 0 order by award_id desc')
    # ret = []
    # for item in applys:
    #     ret.append({
    #         'apply_id': item.apply_id,
    #         'apply_info': item.apply_info,
    #         'award_id': item.award_id,
    #         'organization': item.name,
    #         'apply_award': item.apply_award,
    #         'award_state': item.award_state,
    #         'state': item.state if item.state is not None else '-1',
    #         'apply_time': str(item.apply_time) if item.state is not None else None,
    #     })
    # return ret


def get_my_check(self, user_qq):
    awards = Awards.objects.filter(
        organization__organizationsuser__type=u'0',
        organization__organizationsuser__user=user_qq,
        organization__soft_del=False,
        soft_del=False).all()
    applys = MyApply.objects.filter(award__in=awards).order_by(
        '-id').all().prefetch_related('award', 'award__organization')
    ret = []
    for item in applys:
        ret.append({
            'apply_id': item.id,
            'apply_info': item.apply_info,
            'award_id': item.award.id,
            'organization': item.award.organization.name,
            'apply_award': item.award.name,
            'award_state': item.award.is_active,
            'state': item.state,
            'apply_time': item.apply_time.strftime("%Y-%m-%d %H:%M:%S"),
            'op_user': user_qq if self.get_full_name() is '' else self.get_full_name()
        })
    return ret
