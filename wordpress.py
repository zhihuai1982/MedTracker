# %%
import requests
import json
import re
import base64
import pandas as pd
from datetime import datetime, timedelta

# %%
# trello

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"}

query = {
    'key': 'f45b896485c79fe922e7f022a8bc6f71',
    'token': 'ATTAae59e22e7d144839c54a444aa4f24d4f3ede09405b11ace472e773a78a23b0e8F2D629A2',
}

headers = {
    "Accept": "application/json"
}

# %%
# trello上获取患者住院号列表和id列表，并排除其他无关列表

tpListRaw = requests.request(
    "GET",
    "https://api.trello.com/1/boards/65296c002df7c2c909517c4e/lists",
    headers=headers,
    params=query
).json()

pattern = r'^[A-Za-z0-9]+-[\u4e00-\u9fa5]+-\d+-[\u4e00-\u9fa5]*$'

tpList = [{key: d[key] for key in ['id', 'name']}
          for d in tpListRaw if re.match(pattern, d['name'])]
for item in tpList:
    item['mrn'] = int(item['name'].split('-')[2])


# %%

# 根据住院号获得检查列表
def get_lab_results(mrn, duration):
    hLabList = requests.get(
        f"http://20.21.1.224:5537/api/api//LisReport/GetLisReportIndexHalf/{mrn}/1").json()

    # 根据hLabList里的dodate筛选出大于当前日期-duration（天）的数据
    hLabList = [item for item in hLabList if (
        pd.Timestamp.now() - pd.Timestamp(item['dodate'])).days <= duration]

    totalLabRes = []
    for lab in hLabList:
        url = f"http://20.21.1.224:5537/api/api/LisReport/GetLisReportDetail/{mrn}/{lab['dodate']}/{lab['specimenid']}/{lab['domany']}"
        labRes = requests.get(url).json()
        for item in labRes:
            item['dodate'] = lab['dodate']
            item['checkitem'] = lab['checkitem']
        totalLabRes.extend(labRes)  # 将 labRes 的结果添加到 totalLabRes 列表中

    df = pd.DataFrame(totalLabRes)  # 将 totalLabRes 列表转换为 DataFrame
    df = df[['xmmc', 'jg', 'zdbz', 'ckqj', 'dodate', 'checkitem']]  # 选择需要的列

    def process_group(group):
        if group['zdbz'].replace('', pd.NA).isnull().all():  # 如果 'zdbz' 列都是空白
            return pd.DataFrame([{
                'xmmc': '',
                'jg': 'all阴性',
                'zdbz': '',
                'ckqj': '',
                'dodate': group['dodate'].iloc[0],
                'checkitem': group['checkitem'].iloc[0]
            }])
        else:
            return group[group['zdbz'].replace('', pd.NA).notnull()]  # 删除 'zdbz' 为空白的行

    df = df.groupby('checkitem').apply(process_group).reset_index(drop=True)
    return df

# df = get_lab_results(4878420)
# print(df)

# %%

def get_exam_results(mrn, duration):
    # 根据住院号获取检查结果列表
    hExamList = requests.get(
        f"http://20.21.1.224:5537/api/api/LisReport/GetViewReportIndex/{mrn}/").json()

    # 筛选出hExamList中pacsType非空的字典
    hExamList = [d for d in hExamList if d['pacsType']]

    # 根据hExamList里的repdate筛选出大于当前日期-duration（天）的数据
    hExamList = [item for item in hExamList if (
        pd.Timestamp.now() - pd.Timestamp(item['repdate'])).days <= duration]

    # 根据 hExamList 里的fromdb、repo项目，构建url，格式为 "http://20.21.1.224:5537/api/api/LisReport/Get{Exam['fromdb']}Detail/{mrn}/{Exam['repo']}"
    # 通过request获取具体检查结果，筛选出 checkitem,repdate,repdiag,repcontent
    # 合并输出 dataframe

    totalExamRes = []
    for exam in hExamList:
        url = f"http://20.21.1.224:5537/api/api/LisReport/Get{exam['fromdb']}Detail/{mrn}/{exam['repo']}"
        examRes = requests.get(url).json()
        examRes = {key: examRes[key] for key in [
            'checkitem', 'repdate', 'repdiag', 'repcontent']}
        totalExamRes.append(examRes)

    df = pd.DataFrame(totalExamRes)
    df['repdate'] = pd.to_datetime(df['repdate'])
    df['repdate'] = df['repdate'].dt.strftime('%Y%m%d')
    
    return df



# %%
# https://robingeuens.com/blog/python-wordpress-api/

# url = "https://www.digitalnomad.host:8766/wp-json/wp/v2/posts"
user = "zhihuai1982"
password = "UA5v egrD T2El 9htA c16a SwDA"
credentials = user + ':' + password
token = base64.b64encode(credentials.encode())
header = {'Authorization': 'Basic ' + token.decode('utf-8')}
# response = requests.get(url, headers=header)
# print(response)

url = "https://www.digitalnomad.host:8766/wp-json/wp/v2/posts/109"
post = {
'title' : 'Hello World again',
'status' : 'publish',
'content' : df.to_html()
}
response = requests.post(url , headers=header, json=post)
print(response)

# %%
