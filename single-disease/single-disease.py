# %%

# 读取single-list.xlsx文件，导入到pandas的 DataFrame中

import pandas as pd
import numpy as np

df = pd.read_excel('single-list.xlsx')

# 查看数据的前几行，以确保数据正确导入
df.head()

# %%
# 保留 病种名 列里 “中高危风险患者预防静脉血栓栓塞症（VTE）” 这一行的数据，删除其他行

df = df[df['病种名'] == '中高危风险患者预防静脉血栓栓塞症（VTE）']
# 将出院日期列的数据类型转换为 datetime 类型
df['出院日期'] = pd.to_datetime(df['出院日期'])
# 将出院日期的格式由“2023-09-30 16:19:23”改为“2023”
df['出院日期'] = df['出院日期'].dt.strftime('%Y')
# 将出院日期列的数据类型转换为整数类型
df['出院日期'] = df['出院日期'].astype(int)


# %%

# 出院日期为2023的数据，随机删除1050条数据
# 假设 df 是已经导入的数据框
# 首先筛选出出院日期为 2023 年的数据
df_2023_all = df[df['出院日期'] == 2023]
# 首先筛选出出院日期为 2022 年的数据
df_2022_all = df[df['出院日期'] == 2022]


# %%
# 计算要删除的数据数量
num_to_delete = 900
# 随机选择要删除的数据的索引
indices_to_delete = np.random.choice(
    df_2023_all.index, num_to_delete, replace=False)
# 删除这些索引对应的数据
df_2023_all = df_2023_all.drop(indices_to_delete)

# 出院日期为2022的数据，随机删除1050条数据
# 假设 df 是已经导入的数据框
# 首先筛选出出院日期为 2022 年的数据
df_2022_all = df[df['出院日期'] == 2022]
# 计算要删除的数据数量
num_to_delete = 150
# 随机选择要删除的数据的索引
indices_to_delete = np.random.choice(
    df_2022_all.index, num_to_delete, replace=False)
# 删除这些索引对应的数据
df_2022_all = df_2022_all.drop(indices_to_delete)

# 将两个数据框合并
df_all = pd.concat([df_2023_all, df_2022_all])


# %%
# 查看数据的前几行，以确保数据正确导入

# 创建填报人员列表 fill_list，名单如下
fill_list = [
    '周森浩',
    '赵丽娜',
    '叶荆',
    '叶高飞',
    '项轩',
    '司怡十美',
    '帅冲',
    '秦晨',
    '齐杰',
    '潘虹',
    '金茂',
    '姜晓华',
    '董志怀',
    '岑威',
    '党慧',
    '李洁',
    '金晟曦',
    '吴玉婷',
    '罗媚尹',
    '叶莹莹',
    '顾卓女',
    '徐向龙',
    '叶丽莎',
    '徐竞娴',
    '潘威佑',
    '汤宏博',
    '朱彦臻',
    '张丹',
]

# %%

# df_all 增加一列 “填报人员”，依次从fill_list中抽取一个人填写，满足51条数据后，再从fill_list中抽取一个人填写，直到数据填满为止


def fill_data(df_all, fill_list):
    """
    此函数用于将 fill_list 中的人员填入 df_all 的“填报人员”栏，每个人员填写 51 次
    :param df_all: 输入的数据框
    :param fill_list: 人员名单列表
    :return: 填充后的新数据框
    """
    # 检查 df_all 是否为 DataFrame
    if not isinstance(df_all, pd.DataFrame):
        raise ValueError("df_all 必须是一个 DataFrame")
    # 检查 fill_list 是否为列表
    if not isinstance(fill_list, list):
        raise ValueError("fill_list 必须是一个列表")
    # 计算需要重复的次数
    num_repeats = 53
    # 重复 fill_list 中的元素 51 次
    repeated_list = np.repeat(fill_list, num_repeats)
    # 确保 repeated_list 的长度不超过 df_all 的行数
    repeated_list = repeated_list[:len(df_all)]
    # 将 repeated_list 作为新列添加到 df_all 中
    df_all['填报人员'] = repeated_list
    return df_all


df_all = fill_data(df_all, fill_list)

# %%
# 查看填报人员的人员分布情况
df_all['填报人员'].value_counts()
# %%
# df_select 筛选 姓名 病历号 年龄 性别 病种名 填报人员列
df_select = df_all[['姓名', '病案号', '年龄', '性别', '病种名', '填报人员']]

# %%
# 将df_select 根据不同的填报人员，将数据写入不同的以填报人员名称的excel文件
for i in fill_list:
    df_select[df_select['填报人员'] == i].to_excel(
        i+'.xlsx', index=False)


# %%
