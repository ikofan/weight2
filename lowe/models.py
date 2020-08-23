from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
import datetime
# Create your models here.


# 本表用于初始化每期减重
class StartLowe(models.Model):
    STATUS_ITEMS = [
        (0, '已结束'),
        (1, '本期'),
        (2, '未激活'),
    ]
    batches = models.PositiveIntegerField(verbose_name='期数')
    s_date = models.DateField(verbose_name='开始日期')
    e_date = models.DateField(verbose_name='结束日期')
    status = models.PositiveIntegerField(verbose_name='状态', choices=STATUS_ITEMS, default=2, help_text='如果激活状态，必须到下个月才能把本月设置为0')

    def save(self, *args, **kwargs):
        today = datetime.date.today()
        if self.id:
            # 如果设置本期为0并且已经到了下个月，结束，则要触发以下一系列更新操作
            # if self.batches == 0 and today > self.e_date:
            if self.status == 0:
                # 把本期的减重者的lowe记录调出来
                # 一开始本来用status=1来筛选LoWe，但是本次操作也要更新status为0，所以改用本期的值来筛选。
                lowes = LoWe.objects.filter(batches_id__exact=self.id)
                for lowe in lowes:
                    # 先更新最终体重，且如果要使用.latest()必须要定义get latest by先
                    this_lowe_in_tracker = Tracker.objects.filter(name_id__exact=lowe.name_id).latest()
                    print("His weight is:{}".format(this_lowe_in_tracker.weight))
                    lowe.e_weight = this_lowe_in_tracker.weight
                    # 再更新LoWe完成状态result
                    delta_weight = lowe.s_weight - lowe.e_weight
                    if delta_weight < lowe.target:     # 没有完成目标
                        lowe.result = 0
                        lowe.refund = -lowe.fund
                        # 如果没完成，则押金一半给RC，但是没有考虑所有人没完成的情况，所有人没完成则全部押金给RC，下方会重写这部分
                        lowe.rc_refund = lowe.fund/2
                    elif 0 <= delta_weight - lowe.target < 0.5:    # 完成目标
                        # lowe.objects.update(result=1)
                        # 之前都是上面这种写法，比较一下和下面有啥区别呢？上面那么写总是报错啊
                        lowe.result = 1
                        lowe.rc_refund = 0
                    elif 0.5 <= delta_weight - lowe.target < 1:    # 超过0.5kg
                        # lowe.objects.update(result=2)
                        lowe.result = 2
                        lowe.rc_refund = 0
                    else:       # 超过1kg以上
                        # lowe.objects.update(result=3)
                        lowe.result = 3
                        lowe.refund = 0
                    lowe.save()
                    # if delta_weight < 0.5:     # 没有完成目标
                    #     lowe.objects.update(result=0)
                    #     lowe.refund = -lowe.fund
                    # elif 0.5 <= delta_weight < 1:    # 完成目标
                    #     lowe.objects.update(result=1)
                    # elif 1 <= delta_weight < 1.5:    # 超过0.5kg
                    #     lowe.objects.update(result=2)
                    # else:       # 超过1kg以上
                    #     lowe.objects.update(result=3)
                    #     lowe.refund = 0
                # 考虑全完成和全没完成和部分完成的情况
                people_finished = people_not_finished = 0
                for lowe in lowes:
                    if lowe.result > 0:
                        people_finished += 1
                    else:
                        people_not_finished += 1
                # 全部都完成了的话，奖金为0
                if people_finished == len(lowes):
                    for lowe in lowes:
                        lowe.refund = 0
                        lowe.save()
                # 全部都没完成，扣除所有奖金，归跑步俱乐部
                elif people_not_finished == len(lowes):
                    for lowe in lowes:
                        lowe.refund = -lowe.fund
                        lowe.rc_refund = lowe.fund
                        lowe.save()
                else:
                    # 计算每股奖金: 总罚金/完成人的权重之和（不包含超过1kg完成的人）
                    # get_total_refund是获得罚金的和
                    total_refund = LoWe.get_total_refund(self.id)/2
                    # 拿全额奖金的和半额奖金的人的权重和，用来求每股的价钱
                    full = LoWe.get_refund_weight_full(self.id)
                    half = LoWe.get_refund_weight_half(self.id)
                    finishers_weight = full + half
                    share = round(total_refund / finishers_weight, 2)
                    # 如果有只能那一半奖金的人
                    if half > 0:
                        full_share = round((half * share / 2 + full * share) / full, 2)
                        half_share = round(share / 2, 2)
                    else:
                        full_share = half_share = share

                    for lowe in LoWe.objects.filter(Q(batches_id__exact=self.id) & Q(result__in=[1, 2])):
                        if lowe.result == 1:
                            # lowe.objects.update(refund=full_share*lowe.refund_weight)
                            lowe.refund = full_share*lowe.refund_weight
                        else:
                            # lowe.objects.update(refund=half_share*lowe.refund_weight)
                            lowe.refund = half_share*lowe.refund_weight
                        lowe.save()
        super(StartLowe, self).save(*args, **kwargs)

    def __str__(self):
        return "第{}期".format(self.batches)

    class Meta:
        verbose_name = verbose_name_plural = '减重期数录入'
        get_latest_by = 's_date'


# 本表只是增加名字，有了名字才能操作其他的表，即使不参加也可以不留名字
class Name(models.Model):
    name = models.CharField(max_length=20, verbose_name='姓名')
    owner = models.ForeignKey(User, verbose_name='作者', on_delete=models.CASCADE)
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = verbose_name_plural = '参与者姓名'
        ordering = ['-created_time']


# 本表用于记录每个人每期减重的情况，每个人每期都有一条记录
class LoWe(models.Model):
    SEX_ITEMS = [
        ('M', '男'),
        ('F', '女'),
    ]
    STATUS_ITEMS = [
        (0, '已结束'),
        (1, '本期有效'),
        (2, '退出'),
        (3, '未激活'),
    ]
    RESULT_ITEMS = [
        (0, '未完成'),
        (1, '完成'),
        (2, '完成>0.5kg'),
        (3, '完成>1kg')
    ]

    name = models.ForeignKey(Name, on_delete=models.CASCADE, verbose_name='姓名')
    sex = models.CharField(max_length=4, verbose_name='性别', choices=SEX_ITEMS, default='M')
    batches = models.ForeignKey(StartLowe, on_delete=models.CASCADE, verbose_name='期数')
    status = models.PositiveIntegerField(verbose_name='用户状态', choices=STATUS_ITEMS, default=3)
    s_weight = models.DecimalField(verbose_name='初始体重kg', max_digits=5, decimal_places=2)
    target = models.DecimalField(verbose_name='减重目标kg', max_digits=5, decimal_places=2, help_text='输入要减掉的公斤数，例如1.5')
    # c_weight = models.FloatField(verbose_name='当前体重', help_text='每次打卡输入体重到这里')
    # paid = models.BooleanField(verbose_name='是否付押金', default=False)
    fund = models.IntegerField(verbose_name='押金', null=True, help_text='不要手动填写', blank=True)
    refund_weight = models.PositiveIntegerField(verbose_name='奖金权重', null=True, help_text='不要手动填写', blank=True)
    result = models.PositiveIntegerField('完成状态', choices=RESULT_ITEMS, null=True, help_text='不要手动填写', blank=True)
    # refund+fund 应该=最后拿到的钱
    refund = models.DecimalField(verbose_name='奖金', max_digits=8, decimal_places=2, null=True, help_text='不要手动填写', blank=True)
    rc_refund = models.DecimalField(verbose_name='RC基金', max_digits=8, decimal_places=2, null=True, help_text='不要手动填写', blank=True)
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建日期')
    owner = models.ForeignKey(User, verbose_name='作者', on_delete=models.CASCADE)
    e_weight = models.DecimalField(verbose_name='本期结束体重kg', max_digits=5, decimal_places=2, null=True, help_text='不要手动填写', blank=True)

    def save(self, *args, **kwargs):

        if self.fund is None:
            if self.target < 0.5:
                self.fund = 9999
            elif 0.5 <= self.target < 1:
                self.fund = 150
                self.refund_weight = 1
            elif 1 <= self.target < 1.5:
                self.fund = 125
                self.refund_weight = 2
            elif 1.5 <= self.target < 2:
                self.fund = 100
                self.refund_weight = 3
            elif 2 <= self.target < 2.5:
                self.fund = 75
                self.refund_weight = 4
            else:
                self.fund = 50
                self.refund_weight = 5
        Tracker.objects.create(name=self.name, weight=self.s_weight, check_date=datetime.date.today(), owner=self.owner)

        super(LoWe, self).save(*args, **kwargs)

    # 此处注意一定要用name.name，要不然在保存数据的时候会出错，return的内容必须是str
    def __str__(self):
        return self.name.name

    # 获得第batch_id期总的所有人的押金
    @staticmethod
    def get_total_fund(batch_id):
        # lowes = LoWe.objects.filter(Q(batches_id__exact=batch_id) & Q(status=1))
        lowes = LoWe.objects.filter(batches_id__exact=batch_id)

        # print(lowes)
        total_fund = 0
        for lowe in lowes:
            print(lowe.fund)
            if lowe.fund is None:
                return 0
            else:
                total_fund += lowe.fund
        return total_fund

    # 本期结束后，获得罚款的总金额
    @staticmethod
    def get_total_refund(batch_id):
        lowes = LoWe.objects.filter(batches_id__exact=batch_id)
        total_refund = 0
        for lowe in lowes:
            if lowe.result is None:     # 如果本期没结束，也就还没出结果，就没有refund这一说, return None
                return 0
            else:       # 求出所有没完成的人的押金总额就是奖金总额，具体分的时候再按照权重和完成情况分
                total_refund += lowe.fund if lowe.result == 0 else 0
        return total_refund

    @staticmethod
    # 也包括所有超额完成目标的人
    def get_finisher_count(batch_id):
        lowes = LoWe.objects.filter(batches_id__exact=batch_id)

        for lowe in lowes:
            if lowe.result is None:
                return None
        unfinished = LoWe.objects.filter(result__exact=0)
        return lowes.count() - unfinished.count()

    @staticmethod
    # 能拿到全额奖金的人的权重和
    def get_refund_weight_full(batch_id):
        lowes = LoWe.objects.filter(Q(batches_id__exact=batch_id) & Q(result__exact=1))
        count = 0
        for lowe in lowes:
            count += lowe.refund_weight
        return count
    # 如果没有找到符合条件的人，则返回值就是0

    @staticmethod
    def get_refund_weight_half(batch_id):
        count = 0
        for lowe in LoWe.objects.filter(Q(batches_id__exact=batch_id) & Q(result__exact=2)):
            count += lowe.refund_weight
        return count
    # 如果没有找到符合条件的人，则返回值就是0

    class Meta:
        verbose_name = verbose_name_plural = '每期减重开始时需要录入体重和目标'


# class LoWeKeep(LoWe):
#     fund = models.IntegerField(verbose_name='押金', help_text='不要手动填写', default=100)
#
#     def save(self, *args, **kwargs):
#
#         if self.fund is None:
#
#             if self.target < 0.5:
#                 self.fund = 9999
#             elif 0.5 <= self.target < 1:
#                 self.fund = 150
#                 self.refund_weight = 1
#             elif 1 <= self.target < 1.5:
#                 self.fund = 125
#                 self.refund_weight = 2
#             elif 1.5 <= self.target < 2:
#                 self.fund = 100
#                 self.refund_weight = 3
#             elif 2 <= self.target < 2.5:
#                 self.fund = 75
#                 self.refund_weight = 4
#             else:
#                 self.fund = 50
#                 self.refund_weight = 5
#         Tracker.objects.create(name=self.name, weight=self.s_weight, check_date=datetime.date.today(), owner=self.owner)
#
#         super(LoWe, self).save(*args, **kwargs)


# 本类用于打卡
class Tracker(models.Model):
    check_date = models.DateField(verbose_name='打卡日期')
    name = models.ForeignKey(Name, on_delete=models.CASCADE, verbose_name='姓名')
    weight = models.DecimalField(verbose_name='体重打卡', max_digits=5, decimal_places=2, help_text='录入入体重到这里如82.5')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建日期')
    owner = models.ForeignKey(User, verbose_name='作者', on_delete=models.CASCADE)

    def __str__(self):
        return self.name.name + "打卡"

    class Meta:
        verbose_name = verbose_name_plural = '录入体重打卡'
        # 如果要使用.latest()必须要定义下面的语句
        get_latest_by = 'created_time'
