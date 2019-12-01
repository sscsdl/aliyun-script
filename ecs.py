#!/usr/bin/env python
#coding=utf-8

import datetime
import json
import matplotlib.pyplot as plt
import numpy as np
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkecs.request.v20140526.DescribeSpotPriceHistoryRequest import DescribeSpotPriceHistoryRequest
from aliyunsdkecs.request.v20140526.RunInstancesRequest import RunInstancesRequest
from aliyunsdkecs.request.v20140526.DescribeImagesRequest import DescribeImagesRequest
from aliyunsdkecs.request.v20140526.DescribeInstanceTypesRequest import DescribeInstanceTypesRequest
from aliyunsdkecs.request.v20140526.DescribeSecurityGroupsRequest import DescribeSecurityGroupsRequest
from aliyunsdkecs.request.v20140526.DescribeVSwitchesRequest import DescribeVSwitchesRequest
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkecs.request.v20140526.DeleteInstanceRequest import DeleteInstanceRequest

AccessKeyID = '<access-key-id>'
AccessKeySecret = '<access-key-secret>'

def selectOption(tips, option):
    ### 选择可选项 ###
    for k, v in enumerate(option):
        print(str(k + 1), v[0])
    while True:
        arg = int(input(tips)) - 1
        if arg >=0 and arg < len(option):
            break
    if len(option[arg]) == 2: 
        return option[arg][1]
    else:
        return arg

def instancesList(instanceId = None):
    ### 查看实例 ###
    request = DescribeInstancesRequest()
    request.set_accept_format('json')
    if instanceId:
        request.set_InstanceIds(instanceId) # 可选
    response = client.do_action_with_exception(request)
    return json.loads(response)

def instanceTypesList(typeFamily):
    ### 查看实例规格 ###
    request = DescribeInstanceTypesRequest()
    request.set_accept_format('json')
    request.set_InstanceTypeFamily(typeFamily)

    response = client.do_action_with_exception(request)
    response = json.loads(response)
    # print(json.dumps(response,indent=2))
    return response['InstanceTypes']['InstanceType']

# 选择地域
# https://help.aliyun.com/knowledge_detail/40654.html
RegionId = selectOption('选择地域：', [
    ['深圳', 'cn-shenzhen'],
    ['杭州', 'cn-hangzhou'],
    ['香港', 'cn-hongkong'],
])

client = AcsClient(AccessKeyID, AccessKeySecret, RegionId)

# 选择操作
action = selectOption('选择操作：', [
    ['查看实例'],
    ['创建抢占式实例'],
    ['释放实例'],
])

if action == 0:
    # 查看实例
    res = instancesList()
    print(json.dumps(res,indent=2))

elif action == 1:
    
    # 查看规格 DescribeInstanceTypes

    typeList = ['xn4', 'e4', 'n4', 'mn4', 'e3', 'n1', 'n2'] #
    print("InstanceType \t CPU \t Memory \t GPU \t Bandwidth  \t Pps")
    for i in typeList:
        response = instanceTypesList('ecs.' + i)
        for item in response:
            if 'InstanceBandwidthRx' not in item:
                item['InstanceBandwidthRx'] = 0
            if 'InstancePpsRx' not in item:
                item['InstancePpsRx'] = 0
            print(
                item['InstanceTypeId'], "\t" , 
                item['CpuCoreCount'], "\t", 
                str(int(item['MemorySize'])), "\t", 
                item['GPUAmount'], "\t", 
                str(item['InstanceBandwidthRx']/1024000)+'k', "\t", 
                str(int(item['InstancePpsRx']/10000))+'W', "\t"
            )
    # exit()
    InstanceType = input('输入规格InstanceType：')


    # 查看抢占式实例近30日价格

    request = DescribeSpotPriceHistoryRequest()
    request.set_accept_format('json')

    request.set_NetworkType("vpc")
    request.set_InstanceType(InstanceType)
    day30 = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    request.set_StartTime(day30)

    response = client.do_action_with_exception(request)
    # print(json.dumps(json.loads(response),indent=2))
    response = json.loads(response)
    price = {}
    for i in response['SpotPrices']['SpotPriceType']:
        if i['ZoneId'] in price:
            price[i['ZoneId']].append(i['SpotPrice'])
        else:
            price[i['ZoneId']] = [i['SpotPrice']]
    # 图表
    for i in price:
        plt.plot(price[i], label=i)
    plt.legend()
    plt.title("price")
    plt.show()

    option = []
    for zoneId in price:
        option.append([zoneId, zoneId])
    ZoneId = selectOption('选择可用区：', option)


    # 查询镜像
    ImageOwnerAlias = selectOption('选择镜像：', [
        ['系统', 'system'],
        ['自有', 'self'],
    ])
    print(ImageOwnerAlias)

    request = DescribeImagesRequest()
    request.set_accept_format('json')
    # 镜像类型
    # system：阿里云提供的公共镜像。
    # self：您创建的自定义镜像。
    # others：其他阿里云用户共享给您的镜像。
    # marketplace：镜像市场提供的镜像。您查询到的云市场镜像可以直接使用，无需提前订阅。您需要自行留意云市场镜像的收费详情。
    # request.set_ImageOwnerAlias("system")
    request.set_ImageOwnerAlias(ImageOwnerAlias)
    request.set_OSType("linux")

    response = client.do_action_with_exception(request)
    print(json.dumps(json.loads(response),indent=2))
    # exit()

    ImageId = input('输入镜像ImageId：')
    # print(ImageId)
    # exit()


    # 查看网络安全组
    request = DescribeSecurityGroupsRequest()
    request.set_accept_format('json')
    request.set_NetworkType('vpc') # vpc 专有网络 classic 经典网络

    response = client.do_action_with_exception(request)
    print(json.dumps(json.loads(response),indent=2))
    SecurityGroupId = input('输入网络安全组SecurityGroupId：')
    # exit()

    # SecurityGroupId = 'sg-wz91p7ptv6xmli1thxx5' # normal
    # SecurityGroupId = 'sg-j6c83nnofp3l7cjwwlg7' # open

    # 查看专有网络VPC 交换机
    # https://help.aliyun.com/document_detail/35748.html

    request = DescribeVSwitchesRequest()
    request.set_accept_format('json')

    response = client.do_action_with_exception(request)
    print(json.dumps(json.loads(response),indent=2))
    # exit()

    VSwitchId = input('输入专有网络VPC交换机VSwitchId：')


    # 创建实例
    # https://help.aliyun.com/document_detail/63440.html

    request = RunInstancesRequest()
    request.set_accept_format('json')

    request.set_InstanceName("test")
    request.set_Password("Test123!")
    request.set_ZoneId(ZoneId)
    # InstanceChargeType 实例的付费方式
    # PrePaid：包年包月。
    # PostPaid（默认）：按量付费。
    request.set_InstanceChargeType("PostPaid")
    # InternetChargeType 网络计费类型
    # PayByBandwidth 固定流量  PayByTraffic 按流量计费
    request.set_InternetChargeType("PayByTraffic")
    request.set_InternetMaxBandwidthOut(1) # 出网带宽
    request.set_AutoReleaseTime("2019-12-12T00:00:00Z") # 自动释放时间
    # SpotStrateg 按量实例的抢占策略
    # 当InternetChargeType是PostPaid时有效
    # NoSpot（默认）：正常按量付费实例。
    # SpotWithPriceLimit：设置上限价格的抢占式实例。
    # SpotAsPriceGo：系统自动出价，跟随当前市场实际价格。
    request.set_SpotStrategy("SpotAsPriceGo")
    request.set_ImageId(ImageId)
    request.set_InstanceType(InstanceType)
    request.set_SystemDiskSize("40") # 硬盘，最少20
    # SecurityGroupId 决定了实例的网络类型 
    # 如果指定安全组的网络类型为专有网络VPC，实例则为VPC类型，并同时需要指定参数VSwitchId。
    request.set_SecurityGroupId(SecurityGroupId)
    request.set_VSwitchId(VSwitchId) #vsw-bp1kk71yrvrwvpior0els

    response = client.do_action_with_exception(request)
    response = json.loads(response)
    print(json.dumps(response,indent=2))


    # 查看实例详情
    if 'InstanceIdSets' in response and 'InstanceIdSet' in response['InstanceIdSets']:
        res = instancesList(response['InstanceIdSets']['InstanceIdSet'][0])
        print(json.dumps(res,indent=2))

elif action == 2:

    # 释放实例

    request = DeleteInstanceRequest()
    request.set_accept_format('json')

    request.set_InstanceId("i-wz9a6mtmfnbqfb94b9da")
    request.set_Force(True)

    response = client.do_action_with_exception(request)
    print(json.dumps(json.loads(response),indent=2))

# 没有设置虚拟交换机ID：
# aliyunsdkcore.acs_exception.exceptions.ServerException: HTTP Status: 403 Error:OperationDenied.InvalidNetworkType The specified network type is not available in the specified region.