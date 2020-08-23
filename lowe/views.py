from django.shortcuts import render
from .models import Name, Tracker, LoWe, StartLowe
import datetime
import json
from django.http import HttpResponse, HttpResponseRedirect
from .forms import CheckForm
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.functional import SimpleLazyObject
from django.contrib.auth.models import User
# Create your views here.


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')

        return json.JSONEncoder.default(self, obj)


@login_required(login_url='/account/login/')
def index(request):
    # 如果用status=1过滤StartLowe，一旦本期结束，下一期没开始的时候，主页会出错
    batches = StartLowe.objects.filter(status=1)
    today = datetime.date.today()
    if batches:
        current_batch = batches.first().batches
        lowes = LoWe.objects.filter(batches=current_batch)
        ranks = {}
        # 如果本期还没结束
        if current_batch is not None:
            for lowe in lowes:
                ranks[lowe.name.name] = lowe.s_weight-Tracker.objects.filter(name__exact=lowe.name).latest().weight

            # 只能有一个当期的期数，所有batch[0]，直接写batch.e_date出错说'QuerySet' object has no attribute 'e_date'
            # __sub()__后面别忘了加个.days，要不然不是数字
            days = batches[0].e_date.__sub__(batches[0].s_date).days
            current_days = datetime.date.today().__sub__(batches[0].s_date).days
            # progress = str(round(current_days/days, 2)*100)+'%',用这个语句竟然会得到'7.000000000000001%'，不明觉厉，于是改成下面的
            progress = str(round(current_days / days * 100, 2)) + '%'
            # lowes = LoWe.objects.filter(status=1)
            persons = len(lowes)
            bounus = LoWe.get_total_fund(batches[0].id)
            # first_one
            sorted_rank = sorted(ranks.items(), key=lambda kv: (kv[1], kv[0]))
            if len(sorted_rank) > 2:
                first_one = sorted_rank[-1][0] if sorted_rank[-1][1] != 0 else None
                second_one = sorted_rank[-2][0] if sorted_rank[-2][1] != 0 else None
            else:
                first_one = None
                second_one = None

            context = {
                'progress': progress,
                's_date': batches[0].s_date,
                'e_date': batches[0].e_date,
                'number_of_batch': batches[0].batches,
                'days': days,
                'persons': persons,
                'bounus': bounus,
                'first_one': first_one,
                'second_one': second_one,
                'today': today,

            }
            return render(request, 'lowe/index.html', context)
    else:
        # 如果当前没有期在进行中
        context = {
            'progress': '0',
            's_date': "",
            'e_date': "",
            'number_of_batch': " ",
            'days': 0,
            'persons': 0,
            'bounus': 0,
            'first_one': "",
            'second_one': "",
            'today': today,

        }
        return render(request, 'lowe/index.html', context)


@login_required(login_url='/account/login/')
def tracker(request):
    data_list = [{
        # 得转换为字符串，否则错误
        'name': 'Nobody',
        's_weight': 'Null',
        'target': 'Null',
        'c_weight': 'Null',
        # 'c_date': 'Null',
        'p_weight': 'Null',
        'losed_weight': 'Null',
        # 'complete_rate': str(round((data_info.s_weight - c)/(data_info.s_weight - data_info.target), 2)*100)+'%',
        'complete_rate': 'Null',

    }]
    # 循环找出status=1本期有效的人
    if StartLowe.objects.filter(status=1):
        current_batch = StartLowe.objects.filter(status=1).first().batches
        lowes = LoWe.objects.filter(batches=current_batch)
        if lowes:
            data_list.clear()
            for data_info in lowes:
                # 从打卡数据库中选出姓名相同的同一人的最新体重，Tracker和Lowe都与Name数据库外键链接，引用的时候用name_id滴血认亲
                # 似乎一天内打两个卡数据没啥变化呢
                # c是最新一次打卡体重，也就是当前体重
                c = Tracker.objects.filter(name__exact=data_info.name).latest().weight
                # c_date = Tracker.objects.filter(name__exact=data_info.name).latest().check_date
                # 调试的时候卡在这里，总是报错lowe.models.Tracker.DoesNotExist: Tracker matching query does not exist.
                # 那是因为刚刚加了海光的数据，且没有在打卡数据库中写入
                # print('c = {}'.format(c))
                # 用sub求两个日期的差，大的日期在前面，下面求本期减肥总共天数
                # days = data_info.e_date.__sub__(data_info.s_date)
                # current_days = datetime.date.today().__sub__(data_info.s_date)
                # 字典为列表中的一个元素，相当于表的一行
                losed_weight = c - data_info.s_weight if c is not None else 0
                data_list.append({
                    # 得转换为字符串，否则错误
                    'name': data_info.name.name,
                    's_weight': str(data_info.s_weight),
                    'target': str(data_info.target),
                    'c_weight': str(c),
                    # 'c_date': c_date,
                    'p_weight': str(data_info.s_weight-data_info.target),
                    'losed_weight': str(losed_weight),
                    # 'complete_rate': str(round((data_info.s_weight - c)/(data_info.s_weight - data_info.target), 2)*100)+'%',
                    'complete_rate': str(round(abs(losed_weight) / data_info.target, 2)) if losed_weight<=0 else str(round(-((losed_weight+data_info.target)/data_info.target-1),2)),

                })

    data_dic = {
        'data': data_list
    }

    return HttpResponse(json.dumps(data_dic, cls=MyEncoder, indent=4))


def rules(request):
    return render(request, 'lowe/rules.html')


@login_required(login_url='/account/login/')
def fund_list(request):
    batches = StartLowe.objects.all()
    # 以后不用像下面这么写了，直接调用数据库记录返回就ok
    # data = []
    # for batch in batches:
    #     data.append(
    #         {
    #             'batch': batch.batches,
    #             's_date': batch.s_date,
    #             'e_date': batch.e_date,
    #             'status': batch.status,
    #         }
    #     )
    context = {'batches': batches}

    return render(request, 'lowe/fund_list.html', context=context)


@login_required(login_url='/account/login/')
def fund_details(request, batch_id):
    lowes = LoWe.objects.filter(batches_id__exact=batch_id)
    # 下面本句返回的是一个列表，尽管只有一个元素，所以用first把他去掉列表
    start_lowe = StartLowe.objects.filter(batches=batch_id).first()
    # print(start_lowe, start_lowe[0].batches)
    # 考虑如果所有人都没完成，则罚款归跑步俱乐部，所以就不能/2了
    total_fund = LoWe.get_total_fund(batch_id)
    total_refund = LoWe.get_total_refund(batch_id)

    # 总的罚款=总的押金，也就是所有人都没完成，则rc拿到所有罚金
    if total_refund == total_fund:
        donate_bupt = total_refund
    # 其他情况都是总罚款/2
    else:
        donate_bupt = total_refund/2

    context = {'lowes': lowes,
               'batch': start_lowe,
               'number': len(lowes),
               'total_fund': total_fund,
               'total_refund': total_refund,
               'refund_to_buptrc': donate_bupt,
               'refund_to_finisher': total_refund-donate_bupt,
               }
    return render(request, 'lowe/fund_details.html', context=context)


@login_required(login_url='/account/login/')
def fund(request, fund_id):
    # filter返回的是一个列表，所以尽管只有一个返回值，也还是要用first（）

    current_batch = StartLowe.objects.filter(batches_id=fund_id)
    if current_batch is not None:
        lowes = LoWe.objects.filter(batches=current_batch)
        names = []
        for lowe in lowes:
            names.append({
                'name': lowe.name.name,
                'target': lowe.target,
                'fund': lowe.fund,
                'refund': lowe.refund,
            }
            )

        context = {
            'names': names,
            'batches': current_batch,
            'number': len(lowes),
            'total_fund': LoWe.get_total_fund(current_batch),
            's_date': StartLowe.objects.filter(status=1).first().s_date,
            'e_date': StartLowe.objects.filter(status=1).first().e_date,
            # refund奖金分配还没写
            'refund': 0
        }
        return render(request, 'lowe/fund.html', context=context)
    else:
        context = {
            'names': None,
            'batches': None,
            'number': None,
            'total_fund': None,
            's_date': None,
            'e_date': None,
            'refund': None
        }
        return render(request, 'lowe/fund.html', context=context)


@login_required(login_url='/account/login/')
def check_weight(request):
    # 还不能删掉这个print，user.id属性得先调用一次，才能解包为User对象
    print(request.user.id, type(request.user._wrapped))
    if request.method == 'POST':
        form = CheckForm(request.POST)
        if form.is_valid():
            clean_data = form.cleaned_data
            checks = Tracker()
            checks.name = clean_data['name']
            checks.weight = clean_data['weight']
            checks.owner = request.user._wrapped
            checks.check_date = datetime.date.today()
            print('clean_data:{},name:{},weight:{},owner:{},date:{}'.format(clean_data,clean_data['name'],clean_data['weight'],request.user._wrapped,checks.check_date))
            checks.save()
            return HttpResponseRedirect(reverse('check'))
    else:
        form = CheckForm()

    context = {'form': form}

    return render(request, 'lowe/check_weight.html', context=context)
